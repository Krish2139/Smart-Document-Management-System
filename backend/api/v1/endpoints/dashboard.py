from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.dashboard_service import DashboardService
from backend.schemas.dashboard import DashboardStatisticsResponse
from backend.api.deps import get_current_user_optional
from backend.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/statistics",
    response_model=DashboardStatisticsResponse,
    summary="Dashboard Overview Statistics",
    description="Calculates document totals, storage quota consumption, category distribution, and latest uploads."
)
def get_dashboard_statistics(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> DashboardStatisticsResponse:
    service = DashboardService(db)
    user_id = current_user.id if current_user else None
    user_email = current_user.email if current_user else None
    return service.get_statistics(user_id=user_id, user_email=user_email)
