"""
Custom exception hierarchy for App Garden applications.

This module provides a structured approach to error handling with
user-friendly messages and proper HTTP status codes.
"""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from ..models.base import ErrorDetail, ErrorResponse


class AppError(Exception):
    """
    Base exception class for application errors.

    All custom exceptions should inherit from this class to ensure
    consistent error handling throughout the application.
    """

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_error_detail(self) -> ErrorDetail:
        """Convert exception to ErrorDetail model."""
        return ErrorDetail(
            code=self.code,
            message=self.message,
            details=self.details
        )
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "errors": [self.to_error_detail().model_dump()]
            }
        )


class ValidationError(AppError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )
        self.field = field
    
    def to_error_detail(self) -> ErrorDetail:
        """Include field information in error detail."""
        error_detail = super().to_error_detail()
        error_detail.field = self.field
        return error_detail


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier}
        )


class AuthenticationError(AppError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_REQUIRED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(AppError):
    """Raised when user lacks required permissions."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN
        )


class RateLimitError(AppError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "limit": limit,
                "window": window,
                "retry_after": retry_after
            }
        )


class ExternalServiceError(AppError):
    """Raised when an external service fails."""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service} error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "service": service,
                "original_error": message,
                **(details or {})
            }
        )


class ServiceError(AppError):
    """Raised when a service operation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SERVICE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class AIServiceError(AppError):
    """Raised when AI model operations fail."""

    def __init__(self, message: str, model: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"AI service error: {message}",
            code="AI_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "model": model,
                **(details or {})
            }
        )


class FileError(AppError):
    """Base class for file-related errors."""
    
    def __init__(self, message: str, filename: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FILE_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "filename": filename,
                **(details or {})
            }
        )


class FileSizeError(FileError):
    """Raised when file size exceeds limit."""
    
    def __init__(self, filename: str, size: int, max_size: int):
        super().__init__(
            message=f"File size ({size} bytes) exceeds maximum allowed size ({max_size} bytes)",
            filename=filename,
            details={
                "size": size,
                "max_size": max_size
            }
        )
        self.code = "FILE_TOO_LARGE"


class FileTypeError(FileError):
    """Raised when file type is not allowed."""
    
    def __init__(self, filename: str, file_type: str, allowed_types: List[str]):
        super().__init__(
            message=f"File type '{file_type}' is not allowed. Allowed types: {', '.join(allowed_types)}",
            filename=filename,
            details={
                "file_type": file_type,
                "allowed_types": allowed_types
            }
        )
        self.code = "INVALID_FILE_TYPE"


class AIModelError(AppError):
    """Raised when AI model operations fail."""
    
    def __init__(self, model: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"AI model error ({model}): {message}",
            code="AI_MODEL_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "model": model,
                **(details or {})
            }
        )


class ConfigurationError(AppError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"config_key": config_key} if config_key else None
        )


# Helper functions
def handle_multiple_errors(errors: List[AppError]) -> HTTPException:
    """Convert multiple AppErrors to a single HTTPException."""
    error_details = [error.to_error_detail() for error in errors]
    
    # Use the highest status code from all errors
    status_code = max(error.status_code for error in errors)
    
    return HTTPException(
        status_code=status_code,
        detail={
            "errors": [detail.model_dump() for detail in error_details]
        }
    )