import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owner_id
from app.core.cache import redis_cache
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.db.deps import get_db
from app.schemas import (
    PaginatedResponse,
    PaginationParams,
    ParcelCreate,
    ParcelFilterParams,
    ParcelRead,
)
from app.services import ParcelService

router = APIRouter(prefix="/parcels", tags=["parcels"])

log = logging.getLogger(__name__)


# POST /parcels
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict[str, str],
)
@limiter.limit(settings.RATE_LIMIT_CREATE)
async def register_parcel(
    request: Request,
    body: ParcelCreate,
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(get_owner_id),
):
    """Register a new parcel and persist it to the database."""
    log.info("api_register_parcel_called: owner_id=%s", owner_id)
    parcel = await ParcelService(db).create_from_dto(body, owner_id)
    return {"id": parcel.id, "session_id": owner_id}


# GET /parcels
@router.get(
    "",
    response_model=PaginatedResponse[ParcelRead],
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_LIST)
@redis_cache("parcel_types", ttl=60)
async def list_parcels(
    request: Request,
    pagination: PaginationParams = Depends(),
    filters: ParcelFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(get_owner_id),
):
    """List parcels belonging to the current user/session, with optional filters."""
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


# GET /parcels/{id}
@router.get(
    "/{parcel_id}",
    response_model=ParcelRead,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_DETAIL)
@redis_cache("parcel_types", ttl=60)
async def get_parcel(
    request: Request,
    parcel_id: str,
    db: AsyncSession = Depends(get_db),
    owner_id: str = Depends(get_owner_id),
):
    """Retrieve a single parcel by ID, ensuring it belongs to the caller."""
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
