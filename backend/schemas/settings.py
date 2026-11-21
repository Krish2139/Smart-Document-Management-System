from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str
    email: str
    role: str
    auto_categorize: bool
    duplicate_detection: bool
    default_category: str
    max_upload_size_mb: int = 20
    storage_quota_mb: int = 500


class SettingsUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, max_length=150)
    role: Optional[str] = Field(default=None, max_length=50)
    auto_categorize: Optional[bool] = None
    duplicate_detection: Optional[bool] = None
    default_category: Optional[str] = Field(default=None, max_length=100)
    max_upload_size_mb: Optional[int] = Field(default=None, ge=1, le=100)
    storage_quota_mb: Optional[int] = Field(default=None, ge=10, le=10000)
