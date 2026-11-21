from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.database.base import Base
from backend.models.base import TimestampMixin


class SystemSetting(Base, TimestampMixin):
    """System and Profile Configuration Model."""
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    full_name: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(150), default="")
    role: Mapped[str] = mapped_column(String(50), default="User")
    auto_categorize: Mapped[bool] = mapped_column(Boolean, default=True)
    duplicate_detection: Mapped[bool] = mapped_column(Boolean, default=True)
    default_category: Mapped[str] = mapped_column(String(100), default="Other")
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, default=20)
    storage_quota_mb: Mapped[int] = mapped_column(Integer, default=500)
