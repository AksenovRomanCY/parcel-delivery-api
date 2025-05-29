"""Common auxiliary schemas for errors and pagination responses."""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standardized error payload returned by exception handlers.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable error description.
        details: Optional list of validation or business-rule violations.
    """

    code: str = Field(..., examples=["validation_error"])
    message: str = Field(..., examples=["Payload validation failed"])
    details: Sequence[dict[str, Any]] | None = None


class PaginationParams(BaseModel):
    """Query string parameters for paginating list endpoints.

    Attributes:
        limit: Maximum number of items to return (default: 20, max: 100).
        offset: Number of items to skip from the start (default: 0).
    """

    limit: int = Field(20, ge=1, le=100, description="Number of entries per page")
    offset: int = Field(0, ge=0, description="Offset (how many records to skip)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    Wraps a list of results (`items`) along with metadata used for pagination.

    Attributes:
        items: List of returned objects (type-safe).
        total: Total number of available records.
        limit: Page size originally requested.
        offset: Number of records skipped from start.
    """

    items: list[T]
    total: int
    limit: int
    offset: int
