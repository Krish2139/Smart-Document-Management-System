import io
from datetime import datetime, timedelta, timezone
import pytest


def test_dashboard_statistics_structure(client):
    """
    Verify complete dashboard statistics endpoint structure according to Part 6:
    - total_documents
    - total_storage_used
    - total_categories
    - recent_activity_count
    - category_distribution (documents by category)
    - file_type_distribution (documents by file type)
    - recent_documents (recent uploads)
    - storage_usage_percentage
    """
    response = client.get("/api/dashboard/statistics")
    assert response.status_code == 200
    data = response.json()

    assert "total_documents" in data
    assert "total_storage_used" in data
    assert "total_storage_used_formatted" in data
    assert "storage_usage_percentage" in data
    assert "storage" in data
    assert "used_bytes" in data["storage"]
    assert "quota_bytes" in data["storage"]
    assert "total_categories" in data
    assert "recent_activity_count" in data
    assert "total_activities" in data
    assert "category_distribution" in data
    assert "file_type_distribution" in data
    assert "recent_documents" in data

    assert isinstance(data["category_distribution"], list)
    assert isinstance(data["file_type_distribution"], list)
    assert isinstance(data["recent_documents"], list)


def test_dashboard_live_updates_on_operations(client):
    """
    Verify that dashboard numbers and activity logs update after:
    - Document upload
    - Document download
    - Document category change
    - Document deletion
    """
    # 1. Baseline stats before upload
    base_res = client.get("/api/dashboard/statistics")
    assert base_res.status_code == 200
    base_stats = base_res.json()
    initial_docs = base_stats["total_documents"]
    initial_bytes = base_stats["total_storage_used"]
    initial_acts = base_stats["recent_activity_count"]

    # 2. Upload a new document (e.g. 5000 bytes PDF)
    payload = b"%PDF-1.4 Analytics Test Document Content" + (b"A" * 5000)
    files = {"file": ("Analytics_Exam_Doc.pdf", io.BytesIO(payload), "application/pdf")}
    up_res = client.post("/api/documents", files=files)
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    # Verify dashboard reflects document upload
    after_up_res = client.get("/api/dashboard/statistics")
    after_up = after_up_res.json()
    assert after_up["total_documents"] == initial_docs + 1
    assert after_up["total_storage_used"] == initial_bytes + len(payload)
    assert after_up["recent_activity_count"] == initial_acts + 1

    # Verify file type distribution contains PDF
    pdf_item = next((item for item in after_up["file_type_distribution"] if item["file_type"] == "PDF"), None)
    assert pdf_item is not None
    assert pdf_item["count"] >= 1

    # Verify upload activity was recorded with document ID and description
    act_up = client.get("/api/activities?activity_type=upload&limit=5").json()["items"]
    assert any(a["document_id"] == doc_id and "Analytics_Exam_Doc" in a["document_name"] for a in act_up)

    # 3. Download the document
    dl_res = client.get(f"/api/documents/{doc_id}/download")
    assert dl_res.status_code == 200

    # Verify activity history recorded download with document ID
    act_dl = client.get("/api/activities?activity_type=download&limit=5").json()["items"]
    assert any(a["document_id"] == doc_id and "Analytics_Exam_Doc" in a["document_name"] for a in act_dl)

    # 4. Change category
    cat_patch = client.patch(f"/api/documents/{doc_id}/category", json={"category_name": "Projects"})
    assert cat_patch.status_code == 200

    # Verify category change activity recorded with document ID and description
    act_cat = client.get("/api/activities?activity_type=category&limit=5").json()["items"]
    assert any(a["document_id"] == doc_id and "Projects" in a["description"] for a in act_cat)

    # 5. Delete document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200

    # Verify dashboard totals decremented
    after_del_res = client.get("/api/dashboard/statistics")
    after_del = after_del_res.json()
    assert after_del["total_documents"] == initial_docs
    assert after_del["total_storage_used"] == initial_bytes

    # Verify deletion activity recorded with document ID and description
    act_del = client.get("/api/activities?activity_type=delete&limit=5").json()["items"]
    assert any(a["document_id"] == doc_id and "Analytics_Exam_Doc" in a["document_name"] for a in act_del)


def test_category_lifecycle_activity_logging(client):
    """
    Verify activity history records category creation and category deletion.
    """
    # 1. Create a new custom category
    create_res = client.post("/api/categories", json={
        "name": "Audit_Taxonomy",
        "description": "Category for compliance audit records",
        "color": "#10b981"
    })
    assert create_res.status_code == 201
    cat_id = create_res.json()["id"]

    # Verify category creation activity
    act_create = client.get("/api/activities?activity_type=category_create&limit=5").json()["items"]
    assert any("Audit_Taxonomy" in a["title"] and "compliance audit" in a["description"] for a in act_create)

    # 2. Delete custom category
    del_res = client.delete(f"/api/categories/{cat_id}?reassign_to=Other")
    assert del_res.status_code == 200

    # Verify category deletion activity
    act_delete = client.get("/api/activities?activity_type=category_delete&limit=5").json()["items"]
    assert any("Audit_Taxonomy" in a["title"] for a in act_delete)


def test_activity_history_filtering_and_search(client):
    """
    Verify activity history filters:
    - Activity type filter
    - Search query filter (matching title, description, document_name, or ID)
    - Date range filter (date_from, date_to)
    """
    # 1. Trigger an upload activity with a unique token
    token = "Audit_Token_XYZ987"
    files = {"file": (f"{token}.txt", io.BytesIO(b"Audit trail token test"), "text/plain")}
    up = client.post("/api/documents", files=files)
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # 2. Search by unique token query
    search_res = client.get(f"/api/activities?q={token}")
    assert search_res.status_code == 200
    items = search_res.json()["items"]
    assert len(items) >= 1
    assert any(token in a["document_name"] or token in a["title"] for a in items)

    # 3. Filter by activity_type
    filter_type_res = client.get("/api/activities?activity_type=upload")
    assert filter_type_res.status_code == 200
    for a in filter_type_res.json()["items"]:
        assert a["activity_type"] == "upload"

    # 4. Filter by date range (yesterday to tomorrow)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_res = client.get(f"/api/activities?date_from={yesterday}&date_to={tomorrow}")
    assert date_res.status_code == 200
    assert date_res.json()["total"] >= 1
