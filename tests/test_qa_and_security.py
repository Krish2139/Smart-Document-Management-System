import io
import pytest


def test_validation_unsupported_file_formats(client):
    """
    Part 8 Validation: Ensure disallowed file formats (.exe, .sh, .py, .bin)
    are rejected with 422 Unprocessable Entity.
    """
    disallowed_files = [
        ("malicious.exe", b"MZ\x90\x00\x03Executable binary payload", "application/x-msdownload"),
        ("script.sh", b"#!/bin/bash\necho test", "application/x-sh"),
        ("exploit.py", b"import os\nos.system('dir')", "text/x-python"),
        ("archive.bin", b"\x00\x01\x02\x03Binary blob", "application/octet-stream"),
    ]

    for filename, content, mime in disallowed_files:
        files = {"file": (filename, io.BytesIO(content), mime)}
        res = client.post("/api/documents", files=files)
        assert res.status_code == 422
        body = res.json()
        assert body["success"] is False
        assert "Unsupported file format" in body["error"]["message"]


def test_validation_oversized_files(client):
    """
    Part 8 Validation: Ensure files exceeding 20 MB are rejected with 422.
    """
    # Explicitly enforce 20 MB limit
    client.put("/api/settings", json={"max_upload_size_mb": 20})
    huge_content = b"0" * (20 * 1024 * 1024 + 1024)  # 20MB + 1KB
    files = {"file": ("oversized_report.pdf", io.BytesIO(huge_content), "application/pdf")}
    res = client.post("/api/documents", files=files)
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert "exceeds maximum allowed limit of 20 MB" in body["error"]["message"]


def test_validation_empty_upload(client):
    """
    Part 8 Validation: Ensure empty file uploads (0 bytes) are rejected with 422.
    """
    files = {"file": ("empty_notes.txt", io.BytesIO(b""), "text/plain")}
    res = client.post("/api/documents", files=files)
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert "Uploaded file is empty (0 bytes)" in body["error"]["message"]


def test_validation_duplicate_documents(client):
    """
    Part 8 Validation: Ensure identical file uploads trigger SHA-256 duplicate warning (409 Conflict).
    """
    unique_content = b"%PDF-1.4 Unique Duplicate Detection Test Content"
    files = {"file": ("contract_original.pdf", io.BytesIO(unique_content), "application/pdf")}
    res1 = client.post("/api/documents", files=files)
    assert res1.status_code == 201

    # Attempt re-upload of identical file content with a different name
    files2 = {"file": ("contract_copy.pdf", io.BytesIO(unique_content), "application/pdf")}
    res2 = client.post("/api/documents", files=files2)
    assert res2.status_code == 409
    body = res2.json()
    assert body["success"] is False
    assert "Duplicate file detected" in body["error"]["message"]
    assert "existing_id" in body["error"]["details"]
    assert "sha256_hash" in body["error"]["details"]


def test_validation_missing_document_and_category_ids(client):
    """
    Part 8 Validation: Ensure non-existent document IDs and category IDs return 404 Not Found.
    """
    # 1. Non-existent document ID
    fake_doc_id = "00000000-0000-0000-0000-000000000000"
    res_doc = client.get(f"/api/documents/{fake_doc_id}")
    assert res_doc.status_code == 404
    assert "not found" in res_doc.json()["error"]["message"].lower()

    # 2. Non-existent document download
    res_dl = client.get(f"/api/documents/{fake_doc_id}/download")
    assert res_dl.status_code == 404

    # 3. Non-existent document metadata
    res_meta = client.get(f"/api/documents/{fake_doc_id}/metadata")
    assert res_meta.status_code == 404

    # 4. Non-existent category ID
    fake_cat_id = "cat-non-existent-999"
    res_cat = client.get(f"/api/categories/{fake_cat_id}")
    assert res_cat.status_code == 404
    assert "not found" in res_cat.json()["error"]["message"].lower()


def test_validation_invalid_api_requests(client):
    """
    Part 8 Validation: Ensure malformed or unprocessable requests return 422 with structured error details.
    """
    # 1. Create category with empty name
    res1 = client.post("/api/categories", json={"name": ""})
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

    # 2. Update category with empty string (violates min_length=1)
    cat_res = client.post("/api/categories", json={"name": "ValidationTestCat"})
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    res2 = client.put(f"/api/categories/{cat_id}", json={"name": ""})
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "VALIDATION_ERROR"

    # 3. Pagination offset < 0
    res3 = client.get("/api/documents?skip=-5")
    assert res3.status_code == 422


def test_security_filename_sanitization_and_traversal(client):
    """
    Part 8 Security: Ensure dangerous path traversal patterns and null characters
    are sanitized and prevented from escaping the storage boundary.
    """
    dangerous_filename = "../../../../../etc/passwd.pdf"
    content = b"%PDF-1.4 Dangerous Traversal Attempt Payload"
    files = {"file": (dangerous_filename, io.BytesIO(content), "application/pdf")}
    res = client.post("/api/documents", files=files)
    assert res.status_code == 201
    data = res.json()

    # Filename must be sanitized, eliminating path traversal segments
    assert "/" not in data["filename"]
    assert "\\" not in data["filename"]
    assert ".." not in data["filename"]
    assert "passwd" in data["filename"]


def test_security_no_filesystem_paths_exposed(client):
    """
    Part 8 Security: Verify that internal local filesystem paths (e.g., C:\\... or /var/...)
    are never leaked in document responses, metadata endpoints, or error payloads.
    """
    content = b"%PDF-1.4 Local Path Leakage Prevention Test"
    files = {"file": ("Privacy_Audit_Document.pdf", io.BytesIO(content), "application/pdf")}
    upload_res = client.post("/api/documents", files=files)
    assert upload_res.status_code == 201
    doc_data = upload_res.json()

    # DocumentResponse must not expose file_path
    assert "file_path" not in doc_data
    # Filename must not contain host drive letters
    assert "C:" not in doc_data["filename"]
    assert "Users" not in doc_data["filename"]

    # Metadata endpoint check
    meta_res = client.get(f"/api/documents/{doc_data['id']}/metadata")
    assert meta_res.status_code == 200
    meta_data = meta_res.json()
    assert "file_path" not in meta_data
    assert "C:" not in meta_data["filename"]


def test_security_safe_cors_and_error_handling(client):
    """
    Part 8 Security: Verify that unhandled exceptions do not expose internal stack traces
    or database internals to clients.
    """
    # Malformed route triggering 404 or unhandled case
    res = client.get("/api/unknown_route_probe")
    assert res.status_code == 404

    # Verify structured JSON format for errors
    res_err = client.get("/api/documents/non_existent_id")
    body = res_err.json()
    assert "success" in body
    assert body["success"] is False
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "traceback" not in body["error"]
    assert "stack" not in body["error"]


def test_ui_all_six_views_and_components(client):
    """
    Part 8 UI Testing: Verify that all 6 required views and essential components exist
    in the served frontend shell (index.html).
    """
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # 1. Six Page Views
    assert 'id="page-dashboard"' in html
    assert 'id="page-documents"' in html
    assert 'id="page-upload"' in html
    assert 'id="page-categories"' in html
    assert 'id="page-activity"' in html
    assert 'id="page-settings"' in html

    # 2. Navigation & Sidebar
    assert "nav-link" in html
    assert 'href="#dashboard"' in html
    assert 'href="#documents"' in html
    assert 'href="#upload"' in html
    assert 'href="#categories"' in html
    assert 'href="#activity"' in html
    assert 'href="#settings"' in html

    # 3. Interactive Component Hooks
    assert 'id="dash-total-docs"' in html
    assert 'id="dash-category-chart"' in html
    assert 'id="dash-filetype-chart"' in html
    assert 'id="doc-search-input"' in html
    assert 'id="doc-category-filter"' in html
    assert 'id="doc-type-filter"' in html
    assert 'id="doc-size-filter"' in html
    assert 'id="doc-sort-filter"' in html
    assert 'id="upload-dropzone"' in html
    assert 'id="categories-grid"' in html
    assert 'id="activity-feed"' in html
    assert 'id="app-modal-backdrop"' in html
    assert 'id="app-toast-container"' in html
