from typing import Optional, Any


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 400, code: str = "BAD_REQUEST", details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


class EntityNotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(message=message, status_code=404, code="NOT_FOUND", details=details)


class DuplicateResourceException(AppException):
    def __init__(self, message: str = "Resource already exists", details: Optional[Any] = None):
        super().__init__(message=message, status_code=409, code="CONFLICT", details=details)


class FileValidationException(AppException):
    def __init__(self, message: str = "Invalid file or parameters", details: Optional[Any] = None):
        super().__init__(message=message, status_code=422, code="UNPROCESSABLE_ENTITY", details=details)


class StorageException(AppException):
    def __init__(self, message: str = "Storage operation failed", details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, code="STORAGE_ERROR", details=details)


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None):
        super().__init__(message=message, status_code=401, code="UNAUTHORIZED", details=details)


class AuthorizationException(AppException):
    def __init__(self, message: str = "Access forbidden", details: Optional[Any] = None):
        super().__init__(message=message, status_code=403, code="FORBIDDEN", details=details)
