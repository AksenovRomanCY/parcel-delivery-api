"""Parcel API endpoints for creation, listing, detail, and status updates.

This router handles HTTP concerns for the main parcel workflow. Ownership is
resolved by dependencies and enforced in ``ParcelService`` so route handlers do
not need to know whether the caller is anonymous-session or JWT-based.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owner_id
from app.core.cache import redis_cache
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.db.deps import get_db
from app.models.parcel import Parcel
from app.schemas import (
    PaginatedResponse,
    PaginationParams,
    ParcelCreate,
    ParcelCreateResponse,
    ParcelFilterParams,
    ParcelRead,
)
from app.services import ParcelService

router = APIRouter(prefix="/parcels", tags=["parcels"])

log = logging.getLogger(__name__)


# Create a parcel for the current owner. `owner_id` abstracts over two modes:
# legacy X-Session-Id and JWT user_id, see app/api/deps.py.
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ParcelCreateResponse,
)
@limiter.limit(settings.RATE_LIMIT_CREATE)
async def register_parcel(
    request: Request,
    body: ParcelCreate,
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(get_owner_id),
) -> ParcelCreateResponse:
    """Register a new parcel and persist it to the database.

    The response intentionally echoes ``owner_id`` to make the active ownership
    mode visible to clients and integration tests.
    """
    log.info("api_register_parcel_called: owner_id=%s", owner_id)
    parcel = await ParcelService(db).create_from_dto(body, owner_id)
    return ParcelCreateResponse(id=parcel.id, owner_id=owner_id)


# List responses are cached per owner and query string. The short TTL keeps
# polling cheap while allowing background delivery-cost updates to appear soon.
@router.get(
    "",
    response_model=PaginatedResponse[ParcelRead],
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_LIST)
@redis_cache("parcels", ttl=settings.CACHE_TTL_DEFAULT)
async def list_parcels(
    request: Request,
    pagination: PaginationParams = Depends(),
    filters: ParcelFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(get_owner_id),
) -> PaginatedResponse[ParcelRead]:
    """List parcels belonging to the current user/session, with optional filters.

    Results are cached per owner and query string. The service returns both the
    total count and current page rows so pagination metadata stays consistent.
    """
    total, rows = await ParcelService(db).list_owned(
        owner_id=owner_id,
        filters=filters,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return PaginatedResponse[ParcelRead](
        items=rows,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


# Single-parcel reads use the same owner-aware cache key as list reads.
@router.get(
    "/{parcel_id}",
    response_model=ParcelRead,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_DETAIL)
@redis_cache("parcel", ttl=settings.CACHE_TTL_DEFAULT)
async def get_parcel(
    request: Request,
    parcel_id: str,
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(get_owner_id),
) -> Parcel:
    """Retrieve a single parcel by ID, ensuring it belongs to the caller.

    Unauthorized ownership is intentionally mapped to a generic HTTP error so
    callers cannot infer another user's parcel state from this endpoint.
    """
    log.info("api_get_parcel_called: parcel_id=%s owner_id=%s", parcel_id, owner_id)
    try:
        parcel = await ParcelService(db).get_owned(parcel_id, owner_id)
    except UnauthorizedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"
        ) from None
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        ) from None
    return parcel
