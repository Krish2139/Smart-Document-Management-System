from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    file_extension: str
    mime_type: str
    sha256_hash: str
    category_id: Optional[str] = None
    category_name: str
    is_manually_categorized: bool = False
    user_id: Optional[str] = None
    uploaded_by: Optional[str] = "Anonymous"
    created_at: datetime
    updated_at: datetime


class DocumentCategoryUpdate(BaseModel):
    category_name: str = Field(min_length=1, max_length=100, description="New category name for document")


class DocumentMetadataResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_extension: str
    mime_type: str
    file_size_bytes: int
    file_size_formatted: str
    file_type: str
    sha256_hash: str
    category: str
    is_manually_categorized: bool
    user_id: Optional[str] = None
    uploaded_by: Optional[str] = "Anonymous"
    upload_timestamp: datetime
    is_previewable: bool


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    skip: int
    limit: int


class UploadErrorItem(BaseModel):
    filename: str
    error: str
    code: str


class BatchUploadResponse(BaseModel):
    successful: List[DocumentResponse]
    failed: List[UploadErrorItem]
    total_processed: int
