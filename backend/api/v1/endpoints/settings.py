from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.settings_service import SettingsService
from backend.schemas.settings import SettingsResponse, SettingsUpdate
from backend.models.user import User
from backend.api.deps import get_current_user_optional
from backend.repositories.user_repository import UserRepository

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get system and profile settings",
    description="Retrieve profile details, automated categorization rules, duplicate detection sensitivity, and storage limits."
)
def get_settings(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> SettingsResponse:
    service = SettingsService(db)
    settings_obj = service.get_settings()
    res = SettingsResponse.model_validate(settings_obj)
    if current_user:
        res.full_name = current_user.full_name or current_user.username
        res.email = current_user.email
        res.role = current_user.role
    return res


@router.put(
    "",
    response_model=SettingsResponse,
    summary="Update system and profile settings",
    description="Update profile, automation toggles, and storage limits."
)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> SettingsResponse:
    service = SettingsService(db)
    
    system_payload = payload.model_copy()
    if current_user:
        user_repo = UserRepository(db)
        user_update = {}
        if payload.full_name is not None:
            user_update["full_name"] = payload.full_name
        if payload.email is not None:
            user_update["email"] = payload.email
        if user_update:
            user_repo.update(current_user.id, user_update)
            current_user = user_repo.get_by_id(current_user.id)
        # Prevent individual user's personal details from overwriting global system defaults
        system_payload.full_name = None
        system_payload.email = None

    updated = service.update_settings(system_payload)
    res = SettingsResponse.model_validate(updated)
    if current_user:
        res.full_name = current_user.full_name or current_user.username
        res.email = current_user.email
        res.role = current_user.role
    return res
