from typing import List
from pydantic import BaseModel
from backend.schemas.document import DocumentResponse


class CategoryDistributionItem(BaseModel):
    category_id: str
    category_name: str
    count: int
    percentage: float
    color: str


class FileTypeDistributionItem(BaseModel):
    file_type: str
    count: int
    percentage: float


class StorageUsageStats(BaseModel):
    used_bytes: int
    used_formatted: str
    quota_bytes: int
    quota_formatted: str
    percentage: float


class DashboardStatisticsResponse(BaseModel):
    total_documents: int
    total_storage_used: int
    total_storage_used_formatted: str
    storage_usage_percentage: float
    storage: StorageUsageStats
    total_categories: int
    recent_activity_count: int
    total_activities: int
    category_distribution: List[CategoryDistributionItem]
    file_type_distribution: List[FileTypeDistributionItem]
    recent_documents: List[DocumentResponse]
