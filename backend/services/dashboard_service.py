from typing import List, Optional
from sqlalchemy.orm import Session
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.category_repository import CategoryRepository
from backend.repositories.activity_repository import ActivityRepository
from backend.repositories.settings_repository import SettingsRepository
from backend.schemas.dashboard import (
    DashboardStatisticsResponse,
    CategoryDistributionItem,
    FileTypeDistributionItem,
    StorageUsageStats
)
from backend.schemas.document import DocumentResponse


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.cat_repo = CategoryRepository(db)
        self.act_repo = ActivityRepository(db)
        self.settings_repo = SettingsRepository(db)

    @staticmethod
    def format_bytes(num_bytes: int) -> str:
        if num_bytes == 0:
            return "0.00 KB"
        k = 1024
        sizes = ["Bytes", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(num_bytes, k)))
        i = min(i, len(sizes) - 1)
        p = math.pow(k, i)
        s = round(num_bytes / p, 2)
        return f"{s} {sizes[i]}"

    def get_statistics(self, user_id: Optional[str] = None, user_email: Optional[str] = None) -> DashboardStatisticsResponse:
        self.cat_repo.seed_defaults()

        total_docs = self.doc_repo.count(user_id=user_id)
        used_bytes = self.doc_repo.get_total_size(user_id=user_id)
        sys_settings = self.settings_repo.get_or_create()
        quota_bytes = (sys_settings.storage_quota_mb or 500) * 1024 * 1024

        usage_percentage = round((used_bytes / quota_bytes) * 100, 2) if quota_bytes > 0 else 0.0

        categories_with_counts = self.cat_repo.get_all_with_counts(user_id=user_id)
        total_cats = len(categories_with_counts)
        total_acts = self.act_repo.count(user_email=user_email) if user_email else self.act_repo.count()

        distribution: List[CategoryDistributionItem] = []
        for cat, count in categories_with_counts:
            pct = round((count / total_docs) * 100, 1) if total_docs > 0 else 0.0
            distribution.append(CategoryDistributionItem(
                category_id=cat.id,
                category_name=cat.name,
                count=count,
                percentage=pct,
                color=cat.color or "#7c3aed"
            ))

        file_types = self.doc_repo.get_file_type_counts(user_id=user_id)
        file_type_distribution: List[FileTypeDistributionItem] = []
        for f_type, count in file_types:
            pct = round((count / total_docs) * 100, 1) if total_docs > 0 else 0.0
            file_type_distribution.append(FileTypeDistributionItem(
                file_type=f_type,
                count=count,
                percentage=pct
            ))

        recent_docs_entities = self.doc_repo.get_recent(limit=5, user_id=user_id)
        recent_docs = [DocumentResponse.model_validate(d) for d in recent_docs_entities]

        formatted_used = self.format_bytes(used_bytes)
        storage_stats = StorageUsageStats(
            used_bytes=used_bytes,
            used_formatted=formatted_used,
            quota_bytes=quota_bytes,
            quota_formatted=f"{sys_settings.storage_quota_mb} MB",
            percentage=usage_percentage
        )

        return DashboardStatisticsResponse(
            total_documents=total_docs,
            total_storage_used=used_bytes,
            total_storage_used_formatted=formatted_used,
            storage_usage_percentage=usage_percentage,
            storage=storage_stats,
            total_categories=total_cats,
            recent_activity_count=total_acts,
            total_activities=total_acts,
            category_distribution=distribution,
            file_type_distribution=file_type_distribution,
            recent_documents=recent_docs
        )
