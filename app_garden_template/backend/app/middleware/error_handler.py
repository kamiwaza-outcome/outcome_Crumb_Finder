"""
Global error handling middleware for App Garden applications.

This middleware catches all exceptions and converts them to
consistent error responses.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.errors import AppError
from ..models.base import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to catch and handle all exceptions globally.
    
    This ensures consistent error responses across the application.
    """
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        return response
    
    except Exception as exc:
        return handle_exception(exc, request_id)


def handle_exception(exc: Exception, request_id: str) -> JSONResponse:
    """
    Convert various exception types to consistent JSON responses.
    
    Args:
        exc: The exception to handle
        request_id: Unique request identifier for tracking
        
    Returns:
        JSONResponse with error details
    """
    # Log the full exception
    logger.error(
        f"Request {request_id} failed",
        exc_info=True,
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
    )
    
    # Handle our custom AppError exceptions
    if isinstance(exc, AppError):
        error_response = ErrorResponse(
            errors=[exc.to_error_detail()],
            request_id=request_id
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump()
        )
    
    # Handle FastAPI validation errors
    if isinstance(exc, RequestValidationError):
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body' prefix
            errors.append(ErrorDetail(
                code="VALIDATION_ERROR",
                message=error["msg"],
                field=field,
                details={"type": error["type"]}
            ))
        
        error_response = ErrorResponse(
            errors=errors,
            request_id=request_id
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.model_dump()
        )
    
    # Handle Starlette HTTP exceptions
    if isinstance(exc, StarletteHTTPException):
        error_detail = ErrorDetail(
            code="HTTP_ERROR",
            message=exc.detail if isinstance(exc.detail, str) else "HTTP error occurred",
            details=exc.detail if isinstance(exc.detail, dict) else None
        )
        
        error_response = ErrorResponse(
            errors=[error_detail],
            request_id=request_id
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump()
        )
    
    # Handle all other exceptions as internal server errors
    error_detail = ErrorDetail(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        details={
            "type": type(exc).__name__,
            "request_id": request_id
        }
    )
    
    error_response = ErrorResponse(
        errors=[error_detail],
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


class ErrorHandlerManager:
    """
    Manager for registering custom error handlers.
    
    This allows applications to register handlers for specific
    exception types while maintaining the default behavior.
    """
    
    def __init__(self):
        self._handlers = {}
    
    def register(self, exception_type: type, handler: Callable[[Exception, str], JSONResponse]):
        """
        Register a custom handler for a specific exception type.
        
        Args:
            exception_type: The exception class to handle
            handler: Function that takes (exception, request_id) and returns JSONResponse
        """
        self._handlers[exception_type] = handler
    
    def handle(self, exc: Exception, request_id: str) -> JSONResponse:
        """
        Handle an exception using registered handlers or default behavior.
        
        Args:
            exc: The exception to handle
            request_id: Request ID for tracking
            
        Returns:
            JSONResponse with error details
        """
        # Check for custom handler
        for exc_type, handler in self._handlers.items():
            if isinstance(exc, exc_type):
                return handler(exc, request_id)
        
        # Fall back to default handling
        return handle_exception(exc, request_id)


# Global error handler manager instance
error_handler_manager = ErrorHandlerManager()