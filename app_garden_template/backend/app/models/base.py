"""
Base models and utilities for App Garden applications.

This module provides common Pydantic models and validation utilities
that can be extended for specific application needs.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TimestampedModel(BaseModel):
    """Base model with automatic timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ResponseStatus(str, Enum):
    """Standard response statuses."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class BaseResponse(BaseModel):
    """Base response model for API endpoints."""
    model_config = ConfigDict(protected_namespaces=())
    
    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code for client handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    status: ResponseStatus = Field(default=ResponseStatus.ERROR)
    errors: List[ErrorDetail] = Field(..., description="List of errors")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseResponse):
    """Response model for paginated data."""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


class FileInfo(BaseModel):
    """Information about an uploaded file."""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size: int = Field(..., description="File size in bytes")
    file_id: Optional[str] = Field(None, description="Internal file identifier")


class HealthStatus(BaseModel):
    """Health check status for a service component."""
    healthy: bool = Field(..., description="Whether the component is healthy")
    message: Optional[str] = Field(None, description="Status message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")


class HealthResponse(BaseModel):
    """Complete health check response."""
    status: str = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    components: Dict[str, HealthStatus] = Field(default_factory=dict, description="Component health statuses")
    timestamp: datetime = Field(default_factory=datetime.utcnow)