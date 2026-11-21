from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from backend.models.user import User
from backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: str) -> Optional[User]:
        return self.get_by_id(entity_id)

    def get_by_id(self, entity_id: str) -> Optional[User]:
        return self.db.execute(select(User).where(User.id == entity_id)).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.execute(select(User).where(func.lower(User.email) == email.lower())).scalar_one_or_none()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.execute(select(User).where(func.lower(User.username) == username.lower())).scalar_one_or_none()

    def get_by_identifier(self, identifier: str) -> Optional[User]:
        """Find user by either email or username."""
        ident_lower = identifier.lower().strip()
        return self.db.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == ident_lower,
                    func.lower(User.username) == ident_lower
                )
            )
        ).scalar_one_or_none()

    def list(self, skip: int = 0, limit: int = 100, **kwargs) -> List[User]:
        return list(self.db.execute(select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)).scalars().all())

    def get_all(self, skip: int = 0, limit: int = 100, **kwargs) -> List[User]:
        return self.list(skip=skip, limit=limit, **kwargs)

    def create(self, entity_data: dict) -> User:
        user = User(**entity_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, entity_id: str, update_data: dict) -> Optional[User]:
        user = self.get_by_id(entity_id)
        if not user:
            return None
        for key, val in update_data.items():
            if val is not None:
                setattr(user, key, val)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, entity_id: str) -> bool:
        user = self.get_by_id(entity_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.commit()
        return True

    def count(self) -> int:
        return self.db.execute(select(func.count(User.id))).scalar() or 0
