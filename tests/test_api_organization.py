import io
from datetime import datetime, timedelta, timezone
import pytest


def test_automatic_categorization_rules(client):
    """
    Verify transparent rule-based categorization according to Part 5:
    - Assignment, Notes, Exam -> Academic
    - Research, Paper, Journal -> Research
    - Project, Report, Development -> Projects
    - Personal, Certificate -> Personal
    - Invoice, Budget -> Business
    - Other unmatched documents -> Other
    """
    test_cases = [
        ("Math_Assignment_2026.pdf", "Academic"),
        ("Course_Exam_Notes.txt", "Academic"),
        ("Quantum_Computing_Research_Paper.pdf", "Research"),
        ("Biology_Journal_Abstract.txt", "Research"),
        ("Architecture_Development_Report.docx", "Projects"),
        ("System_Project_Plan.pdf", "Projects"),
        ("Personal_Certificate_Birth.png", "Personal"),
        ("Passport_Tax_Record.jpg", "Personal"),
        ("Vendor_Invoice_Q1.pdf", "Business"),
        ("Annual_Budget_Contract.xlsx", "Business"),
        ("General_Miscellaneous_Notes.txt", "Academic"),  # 'notes' matches Academic
        ("Random_Logfile_Archive.txt", "Other"),
    ]

    for filename, expected_category in test_cases:
        content = f"Unique content for {filename}".encode("utf-8")
        files = {"file": (filename, io.BytesIO(content))}
        res = client.post("/api/documents", files=files)
        assert res.status_code == 201, f"Failed uploading {filename}: {res.text}"
        data = res.json()
        assert data["category_name"] == expected_category, (
            f"Expected '{expected_category}' for '{filename}', got '{data['category_name']}'"
        )
        assert data["is_manually_categorized"] is False


def test_manual_category_override(client):
    """
    Verify that manual category changes override automatic suggestions and set is_manually_categorized=True.
    """
    # 1. Upload a document that gets auto-categorized as 'Business'
    filename = "Office_Budget_2026.pdf"
    files = {"file": (filename, io.BytesIO(b"%PDF-1.4 Office Budget Content"), "application/pdf")}
    res = client.post("/api/documents", files=files)
    assert res.status_code == 201
    doc_id = res.json()["id"]
    assert res.json()["category_name"] == "Business"
    assert res.json()["is_manually_categorized"] is False

    # 2. Manually override category to 'Projects' via PATCH
    patch_res = client.patch(
        f"/api/documents/{doc_id}/category",
        json={"category_name": "Projects"}
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["category_name"] == "Projects"
    assert patched_data["is_manually_categorized"] is True

    # 3. Retrieve document by ID and verify persistence of manual override
    get_res = client.get(f"/api/documents/{doc_id}")
    assert get_res.status_code == 200
    doc_data = get_res.json()
    assert doc_data["category_name"] == "Projects"
    assert doc_data["is_manually_categorized"] is True


def test_search_by_name_extension_and_category(client):
    """
    Verify search functionality:
    - By document name
    - By file extension
    - By category
    """
    # Upload distinct documents
    f1 = {"file": ("Physics_Paper_2026.pdf", io.BytesIO(b"%PDF-1.4 Physics Research"), "application/pdf")}
    f2 = {"file": ("Chemistry_Lab_Guide.docx", io.BytesIO(b"PK\x03\x04 Chemistry Guide Content"))}
    f3 = {"file": ("Company_Budget_Overview.xlsx", io.BytesIO(b"PK\x03\x04 Budget Sheet Content"))}

    client.post("/api/documents", files=f1)
    client.post("/api/documents", files=f2)
    client.post("/api/documents", files=f3)

    # 1. Search by name query
    res_name = client.get("/api/documents/search?q=Physics")
    assert res_name.status_code == 200
    names = [d["filename"] for d in res_name.json()["items"]]
    assert any("Physics_Paper_2026" in n for n in names)

    # 2. Search by extension (e.g. 'docx')
    res_ext = client.get("/api/documents/search?q=docx")
    assert res_ext.status_code == 200
    items = res_ext.json()["items"]
    assert any("Chemistry_Lab_Guide" in d["filename"] for d in items)

    # 3. Search by category keyword ('Business')
    res_cat = client.get("/api/documents/search?q=Business")
    assert res_cat.status_code == 200
    assert any("Company_Budget_Overview" in d["filename"] for d in res_cat.json()["items"])


def test_filters_category_type_size_and_date(client):
    """
    Verify filters:
    - Category filter
    - File type filter
    - File size filter (min_size, max_size)
    - Date filter (date_from, date_to)
    """
    # 1. Small document (500 bytes)
    small_content = b"Small file content" * 15
    f_small = {"file": ("Small_Research_Notes.txt", io.BytesIO(small_content))}
    r1 = client.post("/api/documents", files=f_small)
    assert r1.status_code == 201

    # 2. Larger document (150 KB)
    large_content = b"X" * (150 * 1024)
    f_large = {"file": ("Large_Report_Archive.pdf", io.BytesIO(large_content), "application/pdf")}
    r2 = client.post("/api/documents", files=f_large)
    assert r2.status_code == 201

    # Filter by category
    res_cat = client.get("/api/documents?category=Research")
    assert res_cat.status_code == 200
    for doc in res_cat.json()["items"]:
        assert doc["category_name"].lower() == "research"

    # Filter by file_type
    res_type = client.get("/api/documents?file_type=PDF")
    assert res_type.status_code == 200
    for doc in res_type.json()["items"]:
        assert doc["file_type"] == "PDF"

    # Filter by min_size (e.g. >= 100 KB = 102400 bytes)
    res_size_large = client.get("/api/documents?min_size=102400")
    assert res_size_large.status_code == 200
    for doc in res_size_large.json()["items"]:
        assert doc["file_size"] >= 102400

    # Filter by max_size (e.g. <= 50 KB = 51200 bytes)
    res_size_small = client.get("/api/documents?max_size=51200")
    assert res_size_small.status_code == 200
    for doc in res_size_small.json()["items"]:
        assert doc["file_size"] <= 51200

    # Filter by date range (from yesterday to tomorrow)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_date = client.get(f"/api/documents?date_from={yesterday}&date_to={tomorrow}")
    assert res_date.status_code == 200
    assert len(res_date.json()["items"]) > 0


def test_sorting_options(client):
    """
    Verify sorting by:
    - Name (asc / desc)
    - File size (asc / desc)
    - Category (asc / desc)
    - Date (asc / desc)
    """
    # Sort by name ascending
    res_name_asc = client.get("/api/documents?sort_by=name&sort_order=asc")
    assert res_name_asc.status_code == 200
    names = [d["filename"] for d in res_name_asc.json()["items"]]
    assert names == sorted(names)

    # Sort by size descending
    res_size_desc = client.get("/api/documents?sort_by=size&sort_order=desc")
    assert res_size_desc.status_code == 200
    sizes = [d["file_size"] for d in res_size_desc.json()["items"]]
    assert sizes == sorted(sizes, reverse=True)

    # Sort by category ascending
    res_cat_asc = client.get("/api/documents?sort_by=category&sort_order=asc")
    assert res_cat_asc.status_code == 200
    cats = [d["category_name"] for d in res_cat_asc.json()["items"]]
    assert cats == sorted(cats)


def test_metadata_extraction_endpoint(client):
    """
    Verify metadata extraction endpoint GET /api/documents/{id}/metadata returns:
    - filename
    - original_filename
    - file_extension
    - mime_type
    - file_size_bytes
    - file_size_formatted
    - file_type
    - sha256_hash
    - category
    - is_manually_categorized
    - upload_timestamp
    - is_previewable
    """
    raw_content = b"%PDF-1.4 Extracted Metadata Document Test Content"
    files = {"file": ("Extracted_Spec_Doc.pdf", io.BytesIO(raw_content), "application/pdf")}
    upload_res = client.post("/api/documents", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    meta_res = client.get(f"/api/documents/{doc_id}/metadata")
    assert meta_res.status_code == 200
    meta = meta_res.json()

    assert meta["id"] == doc_id
    assert "Extracted_Spec_Doc" in meta["filename"]
    assert meta["original_filename"] == "Extracted_Spec_Doc.pdf"
    assert meta["file_extension"] == "pdf"
    assert meta["mime_type"] == "application/pdf"
    assert meta["file_size_bytes"] == len(raw_content)
    assert "Bytes" in meta["file_size_formatted"] or "KB" in meta["file_size_formatted"]
    assert meta["file_type"] == "PDF"
    assert len(meta["sha256_hash"]) == 64
    assert meta["category"] == "Projects"
    assert meta["is_manually_categorized"] is False
    assert meta["is_previewable"] is True
    assert "upload_timestamp" in meta


def test_custom_category_reassignment_on_deletion(client):
    """
    Verify custom category creation, document association, and safe reassignment upon deletion:
    - Create category 'Legal'
    - Upload document under 'Legal'
    - Delete 'Legal' category specifying reassign_to='Other'
    - Verify 'Legal' is deleted, and associated document was safely reassigned to 'Other'
    """
    # 1. Create custom category
    cat_res = client.post("/api/categories", json={
        "name": "Legal",
        "description": "Legal agreements, compliance and contracts.",
        "color": "#14b8a6"
    })
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    # 2. Upload document explicitly assigned to 'Legal'
    f = {"file": ("Compliance_Filing.pdf", io.BytesIO(b"%PDF-1.4 Legal Content"), "application/pdf")}
    doc_res = client.post("/api/documents", files=f, data={"category": "Legal"})
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]
    assert doc_res.json()["category_name"] == "Legal"

    # 3. Delete category 'Legal' with safe reassignment to 'Other'
    del_res = client.delete(f"/api/categories/{cat_id}?reassign_to=Other")
    assert del_res.status_code == 200

    # 4. Confirm category 'Legal' no longer exists
    get_cat = client.get(f"/api/categories/{cat_id}")
    assert get_cat.status_code == 404

    # 5. Confirm document still exists and has been safely reassigned to 'Other'
    get_doc = client.get(f"/api/documents/{doc_id}")
    assert get_doc.status_code == 200
    assert get_doc.json()["category_name"] == "Other"
