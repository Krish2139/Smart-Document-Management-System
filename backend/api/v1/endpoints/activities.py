from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.activity_service import ActivityService
from backend.schemas.activity import ActivityResponse, ActivityListResponse
from backend.api.deps import get_current_user_optional
from backend.models.user import User

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get(
    "",
    response_model=ActivityListResponse,
    summary="List activity history",
    description="Retrieve chronological audit trail of document uploads, downloads, deletions, and updates with filters and search."
)
def list_activities(
    q: Optional[str] = Query(None, description="Search keyword in title, description, or document name"),
    activity_type: Optional[str] = Query(None, description="Filter by event type (upload, download, delete, category_change, category_create, category_delete)"),
    date_from: Optional[datetime] = Query(None, description="Start date filter (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="End date filter (ISO format)"),
    since: Optional[datetime] = Query(None, description="ISO timestamp filter"),
    user_email: Optional[str] = Query(None, description="Optional user email filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> ActivityListResponse:
    service = ActivityService(db)
    effective_email = user_email or (current_user.email if current_user else None)
    items, total = service.list_activities(
        query=q,
        activity_type=activity_type,
        date_from=date_from,
        date_to=date_to,
        since=since,
        skip=skip,
        limit=limit,
        user_email=effective_email
    )
    return ActivityListResponse(
        items=[ActivityResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit
    )
