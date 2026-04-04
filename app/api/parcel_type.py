"""Parcel-type API endpoints.

The router contains read-only operations for the reference table
:class:`app.models.parcel_type.ParcelType` and is mounted under the
``/parcel-types`` prefix.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import make_cache_key_no_session, redis_cache
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.db.deps import get_db
from app.schemas import PaginatedResponse, PaginationParams, ParcelTypeRead
from app.services import ParcelTypeService

router = APIRouter(prefix="/parcel-types", tags=["parcel-types"])


@router.get(
    "",
    response_model=PaginatedResponse[ParcelTypeRead],
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_PARCEL_TYPES)
@redis_cache("parcel_types", ttl=60, key_func=make_cache_key_no_session)
async def list_parcel_types(
    request: Request,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of all available parcel types."""
    svc = ParcelTypeService(db)

    total = await svc.total()
    rows = await svc.list_all()

    sliced = rows[pagination.offset : pagination.offset + pagination.limit]

    return PaginatedResponse[ParcelTypeRead](
        items=sliced,
        total=int(total or 0),
        limit=pagination.limit,
        offset=pagination.offset,
    )
