import io
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.document_service import DocumentService
from backend.api.deps import get_current_user_optional
from backend.models.user import User
from backend.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    BatchUploadResponse,
    UploadErrorItem,
    DocumentCategoryUpdate,
    DocumentMetadataResponse
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="Retrieve a paginated list of documents with optional category, file-type, extension, date range, size range, and sorting."
)
def list_documents(
    category: Optional[str] = Query(None, description="Filter by category name"),
    file_type: Optional[str] = Query(None, description="Filter by file type (PDF, WORD, POWERPOINT, EXCEL, IMAGE, TEXT)"),
    file_extension: Optional[str] = Query(None, description="Filter by file extension (e.g. pdf, docx, png)"),
    date_from: Optional[datetime] = Query(None, description="Filter by upload date from (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Filter by upload date to (ISO 8601)"),
    min_size: Optional[int] = Query(None, ge=0, description="Minimum file size in bytes"),
    max_size: Optional[int] = Query(None, ge=0, description="Maximum file size in bytes"),
    sort_by: str = Query("date", description="Sort field: 'date', 'name', 'size', 'category'"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    user_id: Optional[str] = Query(None, description="Optional user ID filter for multi-user isolation"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> DocumentListResponse:
    service = DocumentService(db)
    effective_user_id = user_id or (current_user.id if current_user else None)
    items, total = service.list_documents(
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
        user_id=effective_user_id
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/search",
    response_model=DocumentListResponse,
    summary="Search documents",
    description="Search documents by keyword across filenames, categories, and file extensions with filters and sorting."
)
def search_documents(
    q: str = Query("", description="Search keyword"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    file_type: Optional[str] = Query(None, description="Optional file type filter"),
    file_extension: Optional[str] = Query(None, description="Filter by file extension"),
    date_from: Optional[datetime] = Query(None, description="Upload date from"),
    date_to: Optional[datetime] = Query(None, description="Upload date to"),
    min_size: Optional[int] = Query(None, ge=0, description="Min size in bytes"),
    max_size: Optional[int] = Query(None, ge=0, description="Max size in bytes"),
    sort_by: str = Query("date", description="Sort field: 'date', 'name', 'size', 'category'"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    user_id: Optional[str] = Query(None, description="Optional user ID filter for multi-user isolation"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> DocumentListResponse:
    service = DocumentService(db)
    effective_user_id = user_id or (current_user.id if current_user else None)
    items, total = service.search_documents(
        query=q,
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
        user_id=effective_user_id
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit
    )


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload single document",
    description="Upload a document file with optional category assignment. Validates file format and performs SHA-256 duplicate detection."
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload (PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX, TXT, PNG, JPG/JPEG)"),
    category: Optional[str] = Form(None, description="Optional category name"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    service = DocumentService(db)
    doc = await service.upload_document(file=file, category_name=category, user=current_user)
    return DocumentResponse.model_validate(doc)


@router.post(
    "/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload multiple documents in batch",
    description="Upload multiple documents simultaneously with per-file validation, duplicate detection, and progress reporting."
)
async def upload_documents_batch(
    files: List[UploadFile] = File(..., description="List of document files to upload"),
    category: Optional[str] = Form(None, description="Optional category to apply to all uploaded files"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> BatchUploadResponse:
    service = DocumentService(db)
    result = await service.upload_batch(files=files, category_name=category, user=current_user)
    return BatchUploadResponse(
        successful=[DocumentResponse.model_validate(doc) for doc in result["successful"]],
        failed=[UploadErrorItem(**f) for f in result["failed"]],
        total_processed=result["total_processed"]
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
    description="Retrieve full metadata of a specific document."
)
def get_document(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    service = DocumentService(db)
    user_id = current_user.id if current_user else None
    doc = service.get_document(document_id, user_id=user_id)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/metadata",
    response_model=DocumentMetadataResponse,
    summary="Get extracted document metadata",
    description="Retrieve extracted structural and cryptographic metadata (filename, extension, MIME, size, SHA-256 hash, timestamps)."
)
def get_document_metadata(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> DocumentMetadataResponse:
    service = DocumentService(db)
    user_id = current_user.id if current_user else None
    return service.get_document_metadata(document_id, user_id=user_id)


@router.patch(
    "/{document_id}/category",
    response_model=DocumentResponse,
    summary="Update document category (manual override)",
    description="Manually override the assigned category of a document, marking it as manually categorized."
)
def update_document_category(
    document_id: str,
    payload: DocumentCategoryUpdate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    service = DocumentService(db)
    user_id = current_user.id if current_user else None
    user_email = current_user.email if current_user else None
    doc = service.update_document_category(document_id, payload.category_name, user_id=user_id, user_email=user_email)
    return DocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/download",
    summary="Download original document file",
    description="Download the original uploaded file with its original filename and correct Content-Disposition."
)
def download_document(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    user_id = current_user.id if current_user else None
    user_email = current_user.email if current_user else None
    content, filename, mime_type = service.download_document(document_id, user_id=user_id, user_email=user_email)
    return StreamingResponse(
        io.BytesIO(content),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get(
    "/{document_id}/preview",
    summary="Preview document in browser",
    description="Streams document content inline for browser preview (PDF, Images, Text). Non-previewable types receive appropriate fallback header."
)
def preview_document(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    user_id = current_user.id if current_user else None
    content, filename, mime_type, is_previewable = service.preview_document(document_id, user_id=user_id)

    disposition = "inline" if is_previewable else "attachment"
    return StreamingResponse(
        io.BytesIO(content),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "X-Previewable": "true" if is_previewable else "false"
        }
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete document",
    description="Permanently delete document metadata and its corresponding stored physical file consistently."
)
def delete_document(
    document_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    user_id = current_user.id if current_user else None
    user_email = current_user.email if current_user else None
    service.delete_document(document_id, user_id=user_id, user_email=user_email)
    return {"success": True, "message": f"Document '{document_id}' successfully deleted."}
