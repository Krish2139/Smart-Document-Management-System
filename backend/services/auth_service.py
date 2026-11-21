from typing import Optional
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.repositories.user_repository import UserRepository
from backend.repositories.activity_repository import ActivityRepository
from backend.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    UserProfileUpdateRequest,
    UserChangePasswordRequest
)
from backend.utils.security import (
    hash_password,
    verify_password,
    create_access_token
)
from backend.utils.exceptions import (
    DuplicateResourceException,
    AuthenticationException,
    EntityNotFoundException,
    AppException
)
from backend.utils.logger import logger


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.activity_repo = ActivityRepository(db)

    def register(self, payload: UserRegisterRequest) -> TokenResponse:
        """Register a new user account with duplicate checking."""
        email_clean = payload.email.lower().strip()
        username_clean = payload.username.lower().strip()

        # Check existing email
        if self.user_repo.get_by_email(email_clean):
            raise DuplicateResourceException(f"Account with email '{email_clean}' is already registered.")

        # Check existing username
        if self.user_repo.get_by_username(username_clean):
            raise DuplicateResourceException(f"Username '{username_clean}' is already taken. Please choose another.")

        hashed = hash_password(payload.password)
        role = "admin" if self.user_repo.count() == 0 else (payload.role or "user")

        user = self.user_repo.create({
            "email": email_clean,
            "username": username_clean,
            "full_name": payload.full_name.strip(),
            "hashed_password": hashed,
            "role": role,
            "is_active": True
        })

        # Log activity
        self.activity_repo.create({
            "activity_type": "user_register",
            "title": f"New user registered: {user.username}",
            "description": f"User '{user.full_name}' ({user.email}) successfully created an account with role '{user.role}'.",
            "document_name": "-",
            "category_name": "-",
            "user_email": user.email,
            "status": "Success"
        })

        token_data = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role
        }
        token = create_access_token(token_data)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

    def login(self, payload: UserLoginRequest) -> TokenResponse:
        """Authenticate user by email or username and return JWT access token."""
        identifier = payload.username_or_email.strip()
        user = self.user_repo.get_by_identifier(identifier)

        if not user:
            logger.warning(f"Failed login attempt - user not found: {identifier}")
            raise AuthenticationException("Your username is not correct.")

        if not verify_password(payload.password, user.hashed_password):
            logger.warning(f"Failed login attempt - invalid password for: {identifier}")
            raise AuthenticationException("Your password is not correct.")

        if not user.is_active:
            raise AppException("This account has been deactivated. Please contact support.", status_code=403)

        # Log login activity
        self.activity_repo.create({
            "activity_type": "user_login",
            "title": f"User logged in: {user.username}",
            "description": f"User '{user.full_name}' ({user.email}) successfully logged in.",
            "document_name": "-",
            "category_name": "-",
            "user_email": user.email,
            "status": "Success"
        })

        token_data = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role
        }
        token = create_access_token(token_data)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.user_repo.get_by_id(user_id)

    def update_profile(self, user_id: str, payload: UserProfileUpdateRequest) -> UserResponse:
        """Update user profile details."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)

        update_data = {}
        if payload.full_name is not None and payload.full_name.strip():
            update_data["full_name"] = payload.full_name.strip()

        if payload.email is not None:
            email_clean = payload.email.lower().strip()
            if email_clean != user.email:
                existing = self.user_repo.get_by_email(email_clean)
                if existing and existing.id != user_id:
                    raise DuplicateResourceException(f"Email '{email_clean}' is already in use by another account.")
                update_data["email"] = email_clean

        updated = self.user_repo.update(user_id, update_data)
        return UserResponse.model_validate(updated)

    def change_password(self, user_id: str, payload: UserChangePasswordRequest) -> bool:
        """Change user password after verifying current password."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)

        if not verify_password(payload.current_password, user.hashed_password):
            raise AuthenticationException("Current password is incorrect.")

        new_hash = hash_password(payload.new_password)
        self.user_repo.update(user_id, {"hashed_password": new_hash})
        return True

    def seed_default_admin(self) -> Optional[User]:
        """Seed a default administrator account if database has no registered users."""
        if self.user_repo.count() == 0:
            default_admin = self.user_repo.create({
                "email": "admin@smartdoc.local",
                "username": "admin",
                "full_name": "System Administrator",
                "hashed_password": hash_password("AdminPassword123!"),
                "role": "admin",
                "is_active": True
            })
            logger.info("Default administrator account seeded: admin@smartdoc.local / admin (Password: AdminPassword123!)")
            return default_admin
        return None
