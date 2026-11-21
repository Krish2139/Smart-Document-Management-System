from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.activity import Activity
from backend.repositories.activity_repository import ActivityRepository


class ActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.act_repo = ActivityRepository(db)

    def list_activities(
        self,
        query: Optional[str] = None,
        activity_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        since: Optional[datetime] = None,
        user_email: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Activity], int]:
        items = self.act_repo.get_all(
            skip=skip,
            limit=limit,
            query=query,
            activity_type=activity_type,
            date_from=date_from,
            date_to=date_to,
            since=since,
            user_email=user_email
        )
        total = self.act_repo.count(
            query=query,
            activity_type=activity_type,
            date_from=date_from,
            date_to=date_to,
            since=since,
            user_email=user_email
        )
        return items, total

    def log_activity(
        self,
        activity_type: str,
        title: str,
        description: str = "",
        document_id: Optional[str] = None,
        document_name: str = "-",
        category_name: str = "-",
        status: str = "Success",
        details: str = ""
    ) -> Activity:
        return self.act_repo.create({
            "activity_type": activity_type,
            "title": title,
            "description": description or title,
            "document_id": document_id,
            "document_name": document_name,
            "category_name": category_name,
            "status": status,
            "details": details
        })
