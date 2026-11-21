from sqlalchemy.orm import Session
from backend.models.settings import SystemSetting
from backend.repositories.settings_repository import SettingsRepository
from backend.repositories.activity_repository import ActivityRepository
from backend.schemas.settings import SettingsUpdate


class SettingsService:
    def __init__(self, db: Session):
        self.db = db
        self.settings_repo = SettingsRepository(db)
        self.act_repo = ActivityRepository(db)

    def get_settings(self) -> SystemSetting:
        return self.settings_repo.get_or_create()

    def update_settings(self, update_data: SettingsUpdate) -> SystemSetting:
        cleaned_data = update_data.model_dump(exclude_unset=True)
        filtered_data = {k: v for k, v in cleaned_data.items() if v is not None}
        updated = self.settings_repo.update(entity_id=1, update_data=filtered_data)
        self.act_repo.create({
            "activity_type": "system",
            "title": "Updated system settings",
            "document_name": "-",
            "category_name": "Settings",
            "status": "Success"
        })
        return updated
