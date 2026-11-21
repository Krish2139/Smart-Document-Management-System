import uuid
from typing import Optional
from sqlalchemy import String, Integer, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base
from backend.models.base import TimestampMixin


class Document(Base, TimestampMixin):
    """Document Metadata Model."""
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # PDF, WORD, POWERPOINT, EXCEL, IMAGE, TEXT, OTHER
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False, default="", index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/octet-stream")
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    category_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Other", index=True)
    is_manually_categorized: Mapped[bool] = mapped_column(Boolean, default=False)

    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="Anonymous")

    category_rel: Mapped[Optional["Category"]] = relationship("Category", back_populates="documents")


Index("idx_doc_search", Document.filename, Document.category_name, Document.file_type, Document.file_extension)
