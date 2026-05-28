"""Pydantic schemas used by API request and response models.

Schemas define the external contract of the API: validation, aliases, examples,
and response serialization. ORM models should not be returned directly from new
routes without a schema that documents the payload.
"""

from app.schemas.auth import TokenResponse, UserLogin, UserRead, UserRegister
from app.schemas.common import ErrorResponse, PaginatedResponse, PaginationParams
from app.schemas.parcel import (
    ParcelCreate,
    ParcelCreateResponse,
    ParcelFilterParams,
    ParcelRead,
)
from app.schemas.parcel_type import ParcelTypeRead

__all__ = (
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "UserRead",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
    "ParcelCreate",
    "ParcelCreateResponse",
    "ParcelRead",
    "ParcelFilterParams",
    "ParcelTypeRead",
)
