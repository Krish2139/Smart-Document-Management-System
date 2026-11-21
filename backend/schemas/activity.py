from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    activity_type: str
    title: str
    description: Optional[str] = ""
    document_id: Optional[str] = None
    document_name: Optional[str] = "-"
    category_name: Optional[str] = "-"
    status: str = "Success"
    details: Optional[str] = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow, alias="created_at")
    created_at: datetime


class ActivityListResponse(BaseModel):
    items: List[ActivityResponse]
    total: int
    skip: int = 0
    limit: int = 100
