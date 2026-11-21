from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(default="", max_length=500, description="Description")
    color: Optional[str] = Field(default="#7c3aed", max_length=30, description="Hex color")
    icon: Optional[str] = Field(default="folder", max_length=50, description="Icon identifier")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None, max_length=30)
    icon: Optional[str] = Field(default=None, max_length=50)


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class CategoryWithCountResponse(CategoryResponse):
    document_count: int = 0
