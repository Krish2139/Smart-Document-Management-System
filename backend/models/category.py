import uuid
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base
from backend.models.base import TimestampMixin


class Category(Base, TimestampMixin):
    """Document Category Model."""
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    color: Mapped[str] = mapped_column(String(20), default="#7c3aed")
    icon: Mapped[str] = mapped_column(String(50), default="folder")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="category_rel")
