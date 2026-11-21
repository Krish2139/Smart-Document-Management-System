from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.user import User
from backend.repositories.user_repository import UserRepository
from backend.utils.security import decode_access_token

# Optional OAuth2 scheme: does not raise 401 automatically if Authorization header is missing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Extract and validate current user from Bearer token if present.
    Returns None if no token or token is invalid (enables guest/unauthenticated fallback).
    """
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user or not user.is_active:
        return None

    return user


def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Mandatory authentication dependency.
    Raises HTTP 401 Unauthorized if user is not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or have expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Admin-only role dependency.
    Raises HTTP 403 Forbidden if user is not an administrator.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges are required for this action."
        )
    return current_user
