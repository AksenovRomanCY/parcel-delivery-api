"""Common auxiliary schemes (errors, pagination)."""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    code: str = Field(..., examples=["validation_error"])
    message: str = Field(..., examples=["Payload validation failed"])
    details: Sequence[dict[str, Any]] | None = None


class PaginationParams(BaseModel):
    """Query string parameters for list pagination."""

    limit: int = Field(20, ge=1, le=100, description="Number of entries per page")
    offset: int = Field(0, ge=0, description="Offset (how many records to skip)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Response wrapper with a list of elements and pagination metadata."""

    items: list[T]
    total: int
    limit: int
    offset: int
