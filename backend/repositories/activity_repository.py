from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_
from backend.models.activity import Activity
from backend.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[Activity]):
    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: str) -> Optional[Activity]:
        return self.get_by_id(entity_id)

    def list(self, skip: int = 0, limit: int = 100, **kwargs) -> List[Activity]:
        return self.get_all(skip=skip, limit=limit, **kwargs)

    def get_by_id(self, entity_id: str) -> Optional[Activity]:
        return self.db.execute(select(Activity).where(Activity.id == entity_id)).scalar_one_or_none()

    def _build_filter_conditions(
        self,
        query: Optional[str] = None,
        activity_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        since: Optional[datetime] = None,
        user_email: Optional[str] = None
    ):
        conditions = []

        if user_email:
            conditions.append(Activity.user_email == user_email)
        else:
            conditions.append(Activity.user_email.is_(None))

        if query:
            clean_q = query.strip().lower()
            q_like = f"%{clean_q}%"
            conditions.append(
                or_(
                    func.lower(Activity.title).like(q_like),
                    func.lower(Activity.description).like(q_like),
                    func.lower(Activity.document_name).like(q_like),
                    func.lower(Activity.category_name).like(q_like),
                    func.lower(Activity.activity_type).like(q_like),
                    func.lower(Activity.details).like(q_like)
                )
            )

        if activity_type and activity_type.lower() != "all":
            # Match activity type (handles prefix e.g. 'category' matching category_change, category_create, category_delete)
            act_lower = activity_type.lower()
            if act_lower in {"category", "categories"}:
                conditions.append(func.lower(Activity.activity_type).like("category%"))
            else:
                conditions.append(func.lower(Activity.activity_type) == act_lower)

        if date_from:
            conditions.append(Activity.created_at >= date_from)

        if date_to:
            conditions.append(Activity.created_at <= date_to)

        if since:
            conditions.append(Activity.created_at >= since)

        return conditions

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[str] = None,
        activity_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        since: Optional[datetime] = None,
        user_email: Optional[str] = None
    ) -> List[Activity]:
        stmt = select(Activity)
        conditions = self._build_filter_conditions(
            query=query,
            activity_type=activity_type,
            date_from=date_from,
            date_to=date_to,
            since=since,
            user_email=user_email
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(Activity.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(
        self,
        query: Optional[str] = None,
        activity_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        since: Optional[datetime] = None,
        user_email: Optional[str] = None
    ) -> int:
        stmt = select(func.count(Activity.id))
        conditions = self._build_filter_conditions(
            query=query,
            activity_type=activity_type,
            date_from=date_from,
            date_to=date_to,
            since=since,
            user_email=user_email
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return self.db.execute(stmt).scalar() or 0

    def create(self, entity_data: dict) -> Activity:
        activity = Activity(**entity_data)
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def update(self, entity_id: str, update_data: dict) -> Optional[Activity]:
        act = self.get_by_id(entity_id)
        if not act:
            return None
        for key, val in update_data.items():
            if val is not None:
                setattr(act, key, val)
        self.db.commit()
        self.db.refresh(act)
        return act

    def delete(self, entity_id: str) -> bool:
        act = self.get_by_id(entity_id)
        if not act:
            return False
        self.db.delete(act)
        self.db.commit()
        return True

    def clear_all(self) -> int:
        count = self.db.execute(select(func.count(Activity.id))).scalar() or 0
        self.db.query(Activity).delete()
        self.db.commit()
        return count
