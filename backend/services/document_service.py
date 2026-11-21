import hashlib
import mimetypes
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.models.document import Document
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.category_repository import CategoryRepository
from backend.repositories.activity_repository import ActivityRepository
from backend.repositories.settings_repository import SettingsRepository
from backend.storage import get_storage_provider
from backend.schemas.document import DocumentMetadataResponse
from backend.utils.exceptions import (
    EntityNotFoundException,
    DuplicateResourceException,
    FileValidationException,
    StorageException
)

# Supported extensions strictly according to Part 4 & 5 instructions:
# PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, TXT, PNG, JPG, JPEG
SUPPORTED_EXTENSIONS = {
    "pdf",
    "doc", "docx",
    "ppt", "pptx",
    "xls", "xlsx",
    "txt",
    "png", "jpg", "jpeg"
}

PREVIEWABLE_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt"}

EXTENSION_MIME_MAP = {
    "pdf": ["application/pdf"],
    "doc": ["application/msword", "application/octet-stream"],
    "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip", "application/octet-stream"],
    "ppt": ["application/vnd.ms-powerpoint", "application/octet-stream"],
    "pptx": ["application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/zip", "application/octet-stream"],
    "xls": ["application/vnd.ms-excel", "application/octet-stream"],
    "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip", "application/octet-stream"],
    "txt": ["text/plain", "text/csv", "application/octet-stream"],
    "png": ["image/png"],
    "jpg": ["image/jpeg"],
    "jpeg": ["image/jpeg"]
}


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.cat_repo = CategoryRepository(db)
        self.act_repo = ActivityRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.storage = get_storage_provider()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal and filesystem issues."""
        base_name = Path(filename).name
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
        clean_name = clean_name.lstrip('.')
        return clean_name or f"document_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def detect_file_type(filename: str) -> str:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext == "pdf":
            return "PDF"
        if ext in {"doc", "docx"}:
            return "WORD"
        if ext in {"ppt", "pptx"}:
            return "POWERPOINT"
        if ext in {"xls", "xlsx"}:
            return "EXCEL"
        if ext in {"png", "jpg", "jpeg"}:
            return "IMAGE"
        if ext == "txt":
            return "TEXT"
        return "OTHER"

    @staticmethod
    def suggest_category(filename: str) -> str:
        """
        Transparent rule-based categorization based on keywords in document name:
        - Assignment, Notes, Exam, Syllabus, Course, Lecture → Academic
        - Research, Paper, Journal, Study, Thesis, Abstract → Research
        - Project, Report, Development, Plan, Spec, Architecture → Projects
        - Personal, Certificate, Passport, Resume, CV, ID, Tax → Personal
        - Invoice, Budget, Bill, Contract, Agreement, Receipt, Financial → Business
        - Other unmatched documents → Other
        """
        lower = filename.lower()
        if any(w in lower for w in ["assignment", "notes", "exam", "syllabus", "course", "lecture", "academic", "study_guide"]):
            return "Academic"
        if any(w in lower for w in ["research", "paper", "journal", "thesis", "abstract", "survey", "experiment"]):
            return "Research"
        if any(w in lower for w in ["project", "report", "development", "plan", "spec", "architecture", "roadmap"]):
            return "Projects"
        if any(w in lower for w in ["personal", "certificate", "passport", "resume", "cv", "id", "tax", "medical"]):
            return "Personal"
        if any(w in lower for w in ["invoice", "budget", "bill", "contract", "agreement", "receipt", "financial", "proposal"]):
            return "Business"
        return "Other"

    def is_previewable(self, filename: str) -> bool:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        return ext in PREVIEWABLE_EXTENSIONS

    @staticmethod
    def format_bytes(num_bytes: int) -> str:
        if num_bytes == 0:
            return "0.00 KB"
        k = 1024
        sizes = ["Bytes", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(num_bytes, k)))
        i = min(i, len(sizes) - 1)
        p = math.pow(k, i)
        s = round(num_bytes / p, 2)
        return f"{s} {sizes[i]}"

    async def upload_document(
        self,
        file: UploadFile,
        category_name: Optional[str] = None,
        user: Optional[Any] = None
    ) -> Document:
        raw_filename = file.filename or f"uploaded_{uuid.uuid4().hex[:8]}"
        safe_filename = self.sanitize_filename(raw_filename)
        ext = safe_filename.split(".")[-1].lower() if "." in safe_filename else ""

        # 1. Extension Validation
        if ext not in SUPPORTED_EXTENSIONS:
            allowed_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise FileValidationException(
                f"Unsupported file format '.{ext}'. Supported formats are: {allowed_list}."
            )

        # 2. Content-Type Validation
        claimed_mime = file.content_type
        if claimed_mime and ext in EXTENSION_MIME_MAP:
            expected_mimes = EXTENSION_MIME_MAP[ext]
            if claimed_mime not in expected_mimes and claimed_mime != "application/octet-stream":
                guessed_mime, _ = mimetypes.guess_type(safe_filename)
                if guessed_mime and claimed_mime != guessed_mime:
                    raise FileValidationException(
                        f"Content-Type mismatch: File '.{ext}' was uploaded with invalid MIME type '{claimed_mime}'."
                    )

        # 3. Read content & validate file size (20 MB limit)
        content = await file.read()
        file_size = len(content)

        sys_settings = self.settings_repo.get_or_create()
        max_mb = sys_settings.max_upload_size_mb or 20
        max_bytes = max_mb * 1024 * 1024

        if file_size > max_bytes:
            raise FileValidationException(
                f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit of {max_mb} MB."
            )

        if file_size == 0:
            raise FileValidationException("Uploaded file is empty (0 bytes).")

        # 4. Duplicate Detection via SHA-256 Hash
        sha256_hash = hashlib.sha256(content).hexdigest()
        user_id = getattr(user, "id", None) if user else None
        if sys_settings.duplicate_detection:
            existing_doc = self.doc_repo.get_by_hash(sha256_hash, user_id=user_id)
            if existing_doc:
                raise DuplicateResourceException(
                    f"Duplicate file detected: Identical content already exists in document '{existing_doc.filename}' "
                    f"(Category: {existing_doc.category_name}, Uploaded: {existing_doc.created_at.strftime('%Y-%m-%d %H:%M')}). "
                    f"The file was not re-uploaded.",
                    details={
                        "existing_id": existing_doc.id,
                        "existing_filename": existing_doc.filename,
                        "sha256_hash": sha256_hash
                    }
                )

        # 5. Determine Category & Manual Flag
        is_manual = False
        resolved_category_name = None
        if category_name and category_name.strip() and category_name.lower() != "all":
            resolved_category_name = category_name.strip()
            is_manual = True
        else:
            if sys_settings.auto_categorize:
                resolved_category_name = self.suggest_category(safe_filename)
            else:
                resolved_category_name = sys_settings.default_category or "Other"

        category = self.cat_repo.get_by_name(resolved_category_name)
        if not category:
            category = self.cat_repo.create({
                "name": resolved_category_name,
                "description": f"Category for {resolved_category_name} documents.",
                "color": "#7c3aed"
            })

        # 6. Save with Unique Filename
        doc_id = str(uuid.uuid4())
        unique_storage_filename = f"{doc_id}_{safe_filename}"
        subfolder = category.name.lower()

        try:
            storage_path = self.storage.save_file(
                content=content,
                filename=unique_storage_filename,
                subfolder=subfolder
            )
        except Exception as e:
            raise StorageException(f"Failed to persist document to storage: {str(e)}")

        file_type = self.detect_file_type(safe_filename)
        mime_type, _ = mimetypes.guess_type(safe_filename)
        mime_type = mime_type or claimed_mime or "application/octet-stream"

        user_id = getattr(user, "id", None) if user else None
        uploaded_by = getattr(user, "full_name", None) or getattr(user, "username", None) if user else "Anonymous"
        user_email = getattr(user, "email", None) if user else None

        # 7. Persist Metadata
        try:
            doc = self.doc_repo.create({
                "id": doc_id,
                "filename": safe_filename,
                "original_filename": raw_filename,
                "file_path": storage_path,
                "file_size": file_size,
                "file_type": file_type,
                "file_extension": ext,
                "mime_type": mime_type,
                "sha256_hash": sha256_hash,
                "category_id": category.id,
                "category_name": category.name,
                "is_manually_categorized": is_manual,
                "user_id": user_id,
                "uploaded_by": uploaded_by
            })
        except Exception as e:
            self.storage.delete_file(storage_path)
            raise StorageException(f"Database error while recording document metadata: {str(e)}")

        # 8. Log Activity
        self.act_repo.create({
            "activity_type": "upload",
            "title": f"Uploaded '{doc.filename}' by {uploaded_by}",
            "description": f"Uploaded '{doc.filename}' ({file_type}, {self.format_bytes(file_size)}) by {uploaded_by} to category '{doc.category_name}'",
            "document_id": doc.id,
            "document_name": doc.filename,
            "category_name": doc.category_name,
            "user_email": user_email,
            "status": "Success",
            "details": f"Type: {file_type}, Ext: .{ext}, Size: {file_size} bytes, Uploader: {uploaded_by}, SHA-256: {sha256_hash[:16]}..."
        })

        return doc

    async def upload_batch(self, files: List[UploadFile], category_name: Optional[str] = None, user: Optional[Any] = None) -> Dict[str, Any]:
        successful: List[Document] = []
        failed: List[Dict[str, str]] = []

        for file in files:
            try:
                doc = await self.upload_document(file=file, category_name=category_name, user=user)
                successful.append(doc)
            except Exception as e:
                code = getattr(e, "code", "UPLOAD_ERROR")
                message = getattr(e, "message", str(e))
                failed.append({
                    "filename": file.filename or "unknown",
                    "error": message,
                    "code": code
                })

        return {
            "successful": successful,
            "failed": failed,
            "total_processed": len(files)
        }

    def update_document_category(self, document_id: str, new_category_name: str, user_id: Optional[str] = None, user_email: Optional[str] = None) -> Document:
        """
        Manual category override: updates category and sets is_manually_categorized to True.
        """
        doc = self.get_document(document_id, user_id=user_id)
        target_name = new_category_name.strip()
        if not target_name:
            raise FileValidationException("Category name cannot be empty.")

        category = self.cat_repo.get_by_name(target_name)
        if not category:
            category = self.cat_repo.create({
                "name": target_name,
                "description": f"Category for {target_name} documents.",
                "color": "#7c3aed"
            })

        old_cat = doc.category_name
        updated = self.doc_repo.update(document_id, {
            "category_id": category.id,
            "category_name": category.name,
            "is_manually_categorized": True
        })

        self.act_repo.create({
            "activity_type": "category_change",
            "title": f"Category changed for '{doc.filename}'",
            "description": f"Manually changed category of '{doc.filename}' from '{old_cat}' to '{category.name}'",
            "document_id": doc.id,
            "document_name": doc.filename,
            "category_name": category.name,
            "user_email": user_email,
            "status": "Success",
            "details": f"Previous: {old_cat}, New: {category.name}"
        })

        return updated

    def get_document(self, document_id: str, user_id: Optional[str] = None) -> Document:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID '{document_id}' not found.")
        if user_id and doc.user_id and doc.user_id != user_id:
            raise EntityNotFoundException(f"Document with ID '{document_id}' not found.")
        return doc

    def get_document_metadata(self, document_id: str, user_id: Optional[str] = None) -> DocumentMetadataResponse:
        """Extract and return structured file metadata."""
        doc = self.get_document(document_id, user_id=user_id)
        return DocumentMetadataResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_extension=doc.file_extension,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size,
            file_size_formatted=self.format_bytes(doc.file_size),
            file_type=doc.file_type,
            sha256_hash=doc.sha256_hash,
            category=doc.category_name,
            is_manually_categorized=doc.is_manually_categorized,
            upload_timestamp=doc.created_at,
            is_previewable=self.is_previewable(doc.filename)
        )

    def list_documents(
        self,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None
    ) -> Tuple[List[Document], int]:
        items = self.doc_repo.get_all(
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
            user_id=user_id
        )
        total = self.doc_repo.count(
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            user_id=user_id
        )
        return items, total

    def search_documents(
        self,
        query: str,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        sort_by: str = "date",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None
    ) -> Tuple[List[Document], int]:
        items = self.doc_repo.search(
            query=query,
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
            user_id=user_id
        )
        total = self.doc_repo.count_search(
            query=query,
            category=category,
            file_type=file_type,
            file_extension=file_extension,
            date_from=date_from,
            date_to=date_to,
            min_size=min_size,
            max_size=max_size,
            user_id=user_id
        )
        return items, total

    def download_document(self, document_id: str, user_id: Optional[str] = None, user_email: Optional[str] = None) -> Tuple[bytes, str, str]:
        doc = self.get_document(document_id, user_id=user_id)
        try:
            content = self.storage.get_file(doc.file_path)
        except Exception as e:
            raise StorageException(f"Failed to read document from storage: {str(e)}")

        self.act_repo.create({
            "activity_type": "download",
            "title": f"Downloaded '{doc.original_filename}'",
            "description": f"Downloaded '{doc.original_filename}' ({doc.mime_type})",
            "document_id": doc.id,
            "document_name": doc.original_filename,
            "category_name": doc.category_name,
            "user_email": user_email,
            "status": "Success"
        })
        return content, doc.original_filename, doc.mime_type

    def preview_document(self, document_id: str, user_id: Optional[str] = None) -> Tuple[bytes, str, str, bool]:
        doc = self.get_document(document_id, user_id=user_id)
        try:
            content = self.storage.get_file(doc.file_path)
        except Exception as e:
            raise StorageException(f"Failed to read document from storage: {str(e)}")

        previewable = self.is_previewable(doc.filename)
        return content, doc.filename, doc.mime_type, previewable

    def delete_document(self, document_id: str, user_id: Optional[str] = None, user_email: Optional[str] = None) -> bool:
        doc = self.get_document(document_id, user_id=user_id)
        doc_name = doc.filename
        cat_name = doc.category_name

        try:
            self.storage.delete_file(doc.file_path)
        except Exception:
            pass

        deleted = self.doc_repo.delete(document_id)
        if deleted:
            self.act_repo.create({
                "activity_type": "delete",
                "title": f"Deleted '{doc_name}'",
                "description": f"Permanently deleted document '{doc_name}' from category '{cat_name}'",
                "document_id": document_id,
                "document_name": doc_name,
                "category_name": cat_name,
                "user_email": user_email,
                "status": "Success"
            })
        return deleted
