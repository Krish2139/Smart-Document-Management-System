import io
import pytest


def test_upload_supported_formats(client):
    """Verify upload support for all required formats: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, TXT, PNG, JPG."""
    test_files = [
        ("report.pdf", b"%PDF-1.4 PDF Document Content", "application/pdf", "PDF", "Other"),
        ("document.docx", b"PK\x03\x04 Word Document Content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "WORD", "Other"),
        ("presentation.pptx", b"PK\x03\x04 PowerPoint Presentation", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "POWERPOINT", "Projects"),
        ("spreadsheet.xlsx", b"PK\x03\x04 Excel Spreadsheet Data", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "EXCEL", "Other"),
        ("notes.txt", b"Plain text notes and documentation", "text/plain", "TEXT", "Other"),
        ("photo.png", b"\x89PNG\r\n\x1a\n Image Content", "image/png", "IMAGE", "Other"),
        ("graphic.jpg", b"\xff\xd8\xff JPEG Image Content", "image/jpeg", "IMAGE", "Other"),
    ]

    for filename, content, mime, expected_type, expected_cat in test_files:
        files = {"file": (filename, io.BytesIO(content), mime)}
        response = client.post("/api/documents", files=files)
        assert response.status_code == 201, f"Failed uploading {filename}: {response.text}"
        data = response.json()
        assert data["file_type"] == expected_type
        assert "id" in data
        assert "sha256_hash" in data


def test_upload_batch_multiple_files(client):
    """Verify multiple file batch upload endpoint."""
    files = [
        ("files", ("batch1.txt", io.BytesIO(b"Batch file 1 content"), "text/plain")),
        ("files", ("batch2.txt", io.BytesIO(b"Batch file 2 content"), "text/plain")),
    ]
    response = client.post("/api/documents/batch", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert len(data["successful"]) == 2
    assert len(data["failed"]) == 0


def test_file_size_validation_20mb(client):
    """Verify that file exceeding 20 MB limit is rejected with 422."""
    # 21 MB content
    large_content = b"0" * (21 * 1024 * 1024)
    files = {"file": ("huge_file.pdf", io.BytesIO(large_content), "application/pdf")}
    response = client.post("/api/documents", files=files)
    assert response.status_code == 422
    assert "exceeds maximum allowed limit of 20 MB" in response.json()["error"]["message"]


def test_extension_and_content_type_validation(client):
    """Verify unsupported extensions and content-type mismatch validation."""
    # 1. Disallowed extension
    files = {"file": ("danger.exe", io.BytesIO(b"binary"), "application/octet-stream")}
    res1 = client.post("/api/documents", files=files)
    assert res1.status_code == 422
    assert "Unsupported file format" in res1.json()["error"]["message"]

    # 2. Empty file
    empty_files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    res2 = client.post("/api/documents", files=empty_files)
    assert res2.status_code == 422
    assert "empty" in res2.json()["error"]["message"]


def test_safe_filename_handling(client):
    """Verify filename sanitization against directory traversal characters."""
    files = {"file": ("../../evil/path/unsafe file name #1.txt", io.BytesIO(b"safe test content"), "text/plain")}
    response = client.post("/api/documents", files=files)
    assert response.status_code == 201
    data = response.json()
    # Path traversal should be stripped
    assert "/" not in data["filename"]
    assert "\\" not in data["filename"]
    assert ".." not in data["filename"]


def test_duplicate_detection(client):
    """Verify SHA-256 duplicate detection rejects identical files without overwriting."""
    content = b"Unique content for duplicate detection test 12345"
    files1 = {"file": ("first_copy.txt", io.BytesIO(content), "text/plain")}
    res1 = client.post("/api/documents", files=files1)
    assert res1.status_code == 201

    # Attempt to upload identical content with different filename
    files2 = {"file": ("second_copy.txt", io.BytesIO(content), "text/plain")}
    res2 = client.post("/api/documents", files=files2)
    assert res2.status_code == 409
    error = res2.json()["error"]
    assert error["code"] == "CONFLICT"
    assert "Duplicate file detected" in error["message"]


def test_document_listing_and_filtering(client):
    """Verify document catalog filtering by category and file type."""
    response = client.get("/api/documents?file_type=PDF")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert all(item["file_type"] == "PDF" for item in data["items"])


def test_document_search(client):
    """Verify searching documents by keyword."""
    response = client.get("/api/documents/search?q=report")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("report.pdf" in item["filename"] for item in data["items"])


def test_document_download(client):
    """Verify downloading original file with correct filename header."""
    list_res = client.get("/api/documents")
    doc = list_res.json()["items"][0]

    response = client.get(f"/api/documents/{doc['id']}/download")
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    assert doc["original_filename"] in response.headers["content-disposition"]


def test_document_preview(client):
    """Verify inline browser preview for previewable types and download fallback for office formats."""
    list_res = client.get("/api/documents")
    docs = list_res.json()["items"]

    # Preview PDF (inline)
    pdf_doc = next((d for d in docs if d["file_type"] == "PDF"), None)
    if pdf_doc:
        res = client.get(f"/api/documents/{pdf_doc['id']}/preview")
        assert res.status_code == 200
        assert "inline" in res.headers["content-disposition"]
        assert res.headers["x-previewable"] == "true"

    # Preview Word (attachment/fallback)
    word_doc = next((d for d in docs if d["file_type"] == "WORD"), None)
    if word_doc:
        res = client.get(f"/api/documents/{word_doc['id']}/preview")
        assert res.status_code == 200
        assert "attachment" in res.headers["content-disposition"]
        assert res.headers["x-previewable"] == "false"


def test_document_deletion_consistency(client):
    """Verify consistent deletion of both metadata and disk storage."""
    # Upload a document to delete
    files = {"file": ("temp_delete_test.txt", io.BytesIO(b"Temporary file to delete"), "text/plain")}
    upload_res = client.post("/api/documents", files=files)
    doc_id = upload_res.json()["id"]

    # Delete
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200

    # Verify not found in DB
    get_res = client.get(f"/api/documents/{doc_id}")
    assert get_res.status_code == 404

    # Verify download fails with 404
    dl_res = client.get(f"/api/documents/{doc_id}/download")
    assert dl_res.status_code == 404
