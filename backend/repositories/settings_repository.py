from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.settings import SystemSetting
from backend.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[SystemSetting]):
    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: int = 1) -> Optional[SystemSetting]:
        return self.get_by_id(entity_id)

    def list(self, skip: int = 0, limit: int = 100, **kwargs):
        return self.get_all(skip=skip, limit=limit)

    def get_by_id(self, entity_id: int = 1) -> Optional[SystemSetting]:
        return self.db.execute(select(SystemSetting).where(SystemSetting.id == entity_id)).scalar_one_or_none()

    def get_all(self, skip: int = 0, limit: int = 100):
        setting = self.get_or_create()
        return [setting]

    def get_or_create(self) -> SystemSetting:
        setting = self.db.execute(select(SystemSetting).where(SystemSetting.id == 1)).scalar_one_or_none()
        if not setting:
            setting = SystemSetting(id=1)
            self.db.add(setting)
            self.db.commit()
            self.db.refresh(setting)
        return setting

    def create(self, entity_data: dict) -> SystemSetting:
        setting = SystemSetting(**entity_data)
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def update(self, entity_id: int = 1, update_data: dict = None) -> SystemSetting:
        setting = self.get_or_create()
        if update_data:
            for key, val in update_data.items():
                if val is not None:
                    setattr(setting, key, val)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def delete(self, entity_id: int) -> bool:
        return False  # System settings row should not be dropped
