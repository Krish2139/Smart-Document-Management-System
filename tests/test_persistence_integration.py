import io
import os
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.document import Document
from backend.models.category import Category
from backend.models.activity import Activity
from backend.models.settings import SystemSetting
from backend.services.document_service import DocumentService
from backend.services.category_service import CategoryService
from backend.services.activity_service import ActivityService
from backend.storage.local import LocalStorageProvider


def test_complete_data_persistence_and_restart_lifecycle(tmp_path):
    """
    Test 2 & Testing requirement:
    Simulates complete application lifecycle and restart:
    1. Initialize fresh SQLite database and storage in a persistent temp path.
    2. Upload documents with automatic categorization.
    3. Create custom category and manually reassign a document.
    4. Download a document and verify activity logging.
    5. Delete one document.
    6. SIMULATE APPLICATION RESTART:
       - Dispose engine, drop connections.
       - Re-initialize new engine and Session pointing to the same SQLite file.
    7. VERIFY:
       - Preserved documents and metadata still exist after restart.
       - Deleted document does NOT reappear in listings.
       - Custom categories still exist with correct document associations.
       - Stored physical files exist in local disk storage.
       - Complete activity audit history persists with timestamps and descriptions.
    """
    db_file = tmp_path / "persistence_test.db"
    storage_dir = tmp_path / "storage_files"
    storage_dir.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_file.as_posix()}"

    # --- SESSION 1 (Before Restart) ---
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine1)
    Session1 = sessionmaker(autocommit=False, autoflush=False, bind=engine1)
    db1 = Session1()

    storage1 = LocalStorageProvider(base_dir=str(storage_dir))
    doc_service1 = DocumentService(db1)
    doc_service1.storage = storage1

    cat_service1 = CategoryService(db1)
    act_service1 = ActivityService(db1)

    # 1. Create a custom category 'Engineering'
    from backend.schemas.category import CategoryCreate
    eng_cat = cat_service1.create_category(CategoryCreate(
        name="Engineering",
        description="Blueprints and architecture diagrams",
        color="#3b82f6"
    ))
    assert eng_cat.name == "Engineering"

    # 2. Upload Document A (Auto-categorized as 'Research')
    content_a = b"%PDF-1.4 Machine Learning Research Paper Content"
    from fastapi import UploadFile
    import asyncio

    upload_file_a = UploadFile(
        file=io.BytesIO(content_a),
        filename="Machine_Learning_Research_Paper.pdf",
        headers={"content-type": "application/pdf"}
    )
    doc_a = asyncio.run(doc_service1.upload_document(upload_file_a))
    assert doc_a.category_name == "Research"
    assert doc_a.is_manually_categorized is False
    doc_a_id = doc_a.id
    doc_a_path = doc_a.file_path

    # 3. Upload Document B (Auto-categorized as 'Academic', then manually overridden to 'Engineering')
    content_b = b"%PDF-1.4 Course Exam Syllabus Document"
    upload_file_b = UploadFile(
        file=io.BytesIO(content_b),
        filename="Course_Exam_Syllabus.pdf",
        headers={"content-type": "application/pdf"}
    )
    doc_b = asyncio.run(doc_service1.upload_document(upload_file_b))
    doc_b_id = doc_b.id
    # Manually reassign to 'Engineering'
    doc_service1.update_document_category(doc_b_id, "Engineering")

    # 4. Upload Document C (To be deleted)
    content_c = b"Temporary plain text notes to be deleted"
    upload_file_c = UploadFile(
        file=io.BytesIO(content_c),
        filename="Temporary_Scratch_Notes.txt",
        headers={"content-type": "text/plain"}
    )
    doc_c = asyncio.run(doc_service1.upload_document(upload_file_c))
    doc_c_id = doc_c.id
    doc_c_path = doc_c.file_path

    # Verify physical files exist before deletion
    assert storage1.file_exists(doc_a_path) is True
    assert storage1.file_exists(doc_c_path) is True

    # 5. Delete Document C
    deleted = doc_service1.delete_document(doc_c_id)
    assert deleted is True
    assert storage1.file_exists(doc_c_path) is False

    # Download Document A (logs download activity)
    dl_content, dl_name, _ = doc_service1.download_document(doc_a_id)
    assert dl_content == content_a

    # Count activities before restart
    acts_before = act_service1.act_repo.count()
    assert acts_before >= 5

    # Close and dispose Session 1 (simulating process termination)
    db1.close()
    engine1.dispose()

    # --- SESSION 2 (After Application Restart) ---
    engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
    Session2 = sessionmaker(autocommit=False, autoflush=False, bind=engine2)
    db2 = Session2()

    storage2 = LocalStorageProvider(base_dir=str(storage_dir))
    doc_service2 = DocumentService(db2)
    doc_service2.storage = storage2
    cat_service2 = CategoryService(db2)
    act_service2 = ActivityService(db2)

    # Verification 1: Document A metadata and physical file persisted
    persisted_a = doc_service2.get_document(doc_a_id)
    assert persisted_a is not None
    assert persisted_a.filename == "Machine_Learning_Research_Paper.pdf"
    assert persisted_a.category_name == "Research"
    assert persisted_a.file_extension == "pdf"
    assert persisted_a.file_type == "PDF"
    assert persisted_a.file_size == len(content_a)
    assert storage2.file_exists(persisted_a.file_path) is True
    assert storage2.get(persisted_a.file_path) == content_a

    # Verification 2: Document B manual category override persisted
    persisted_b = doc_service2.get_document(doc_b_id)
    assert persisted_b is not None
    assert persisted_b.category_name == "Engineering"
    assert persisted_b.is_manually_categorized is True

    # Verification 3: Deleted Document C does NOT appear in listings or get_by_id
    all_docs, total_count = doc_service2.list_documents()
    assert total_count == 2
    doc_ids = [d.id for d in all_docs]
    assert doc_a_id in doc_ids
    assert doc_b_id in doc_ids
    assert doc_c_id not in doc_ids

    # Verification 4: Custom Category 'Engineering' persisted
    cats_with_counts = cat_service2.get_all_with_counts()
    cat_names = [c[0].name for c in cats_with_counts]
    assert "Engineering" in cat_names
    eng_tuple = next(c for c in cats_with_counts if c[0].name == "Engineering")
    assert eng_tuple[1] == 1  # 1 document assigned to Engineering

    # Verification 5: Activities persisted after restart
    activities, act_count = act_service2.list_activities()
    assert act_count == acts_before
    act_types = [a.activity_type for a in activities]
    assert "upload" in act_types
    assert "download" in act_types
    assert "delete" in act_types
    assert "category_change" in act_types or "category" in act_types
    assert "category_create" in act_types

    # Clean up Session 2
    db2.close()
    engine2.dispose()
