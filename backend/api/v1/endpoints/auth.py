from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.user import User
from backend.api.deps import get_current_user
from backend.services.auth_service import AuthService
from backend.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    UserProfileUpdateRequest,
    UserChangePasswordRequest
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="Create a new user account with unique username and email, returning a JWT access token."
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    return service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User sign in / login",
    description="Authenticate with username/email and password to receive a JWT access token."
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    return service.login(payload)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve the profile details of the currently authenticated user."
)
def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update user profile",
    description="Update full name or email of the currently authenticated user."
)
def update_profile(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserResponse:
    service = AuthService(db)
    return service.update_profile(current_user.id, payload)


@router.post(
    "/change-password",
    summary="Change account password",
    description="Change account password after validating current password."
)
def change_password(
    payload: UserChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    service.change_password(current_user.id, payload)
    return {"success": True, "message": "Password changed successfully."}


@router.post(
    "/logout",
    summary="Sign out / Logout",
    description="Log out active session. Client discards JWT token."
)
def logout():
    return {"success": True, "message": "Signed out successfully."}
