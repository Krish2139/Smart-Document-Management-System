from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class UserBase(BaseModel):
    email: str = Field(description="User primary email address")
    username: str = Field(min_length=3, max_length=50, description="Unique account username")
    full_name: str = Field(min_length=1, max_length=100, description="User full display name")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if "@" not in v_clean or "." not in v_clean.split("@")[-1]:
            raise ValueError("Invalid email address format.")
        return v_clean


class UserRegisterRequest(UserBase):
    password: str = Field(min_length=6, max_length=100, description="Account password (min 6 chars)")
    role: Optional[str] = Field(default="user", description="Account role: 'user' or 'admin'")


class UserLoginRequest(BaseModel):
    username_or_email: str = Field(min_length=1, description="Username or registered email address")
    password: str = Field(min_length=1, description="Account password")


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    is_active: bool
    avatar_url: Optional[str] = ""
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip().lower()
        if "@" not in v_clean or "." not in v_clean.split("@")[-1]:
            raise ValueError("Invalid email address format.")
        return v_clean


class UserChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=100)
