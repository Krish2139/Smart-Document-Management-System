import uuid
from typing import Optional
from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base
from backend.models.base import TimestampMixin


class Activity(Base, TimestampMixin):
    """Audit Activity History Log Model."""
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # upload, download, delete, category_change, category_create, category_delete
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    document_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="-")
    category_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="-")
    user_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Success")
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")


Index("idx_activity_type_time", Activity.activity_type, Activity.created_at)
