import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_id
from app.core.cache import redis_cache
from app.core.exceptions import NotFoundError, UnauthorizedError
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
async def register_parcel(
    body: ParcelCreate,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Register a new parcel and persist it to the database.

    Validates that weight is positive and stores session ownership.

    Args:
        body: Validated request body containing parcel fields.
        db: Active database session (injected).
        session_id: Anonymous user/session identifier (from middleware).

    Returns:
        dict[str, session_id]: ID of the newly created parcel.
    """
    log.info("api_register_parcel_called: session_id=%s", session_id)
    parcel = await ParcelService(db).create_from_dto(body, session_id)
    return {"id": parcel.id, "session_id": session_id}


# GET /parcels
@router.get(
    "",
    response_model=PaginatedResponse[ParcelRead],
    status_code=status.HTTP_200_OK,
)
@redis_cache("parcel_types", ttl=60)
async def list_parcels(
    request: Request,  # noqa
    pagination: PaginationParams = Depends(),
    filters: ParcelFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """List parcels belonging to the current session, with optional filters.

    Supports pagination and filtering by parcel type and delivery-cost
    presence.

    Args:
        request: is used for caching.
        pagination: ``limit`` and ``offset`` query parameters.
        filters: Filter options parsed from query string.
        db: Active database session.
        session_id: Current session identifier.

    Returns:
        PaginatedResponse[ParcelRead]: List of parcels and metadata.
    """
    total, rows = await ParcelService(db).list_owned(
        session_id=session_id,
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
@redis_cache("parcel_types", ttl=60)
async def get_parcel(
    request: Request,  # noqa
    parcel_id: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Retrieve a single parcel by ID, ensuring it belongs to the session.

    Args:
        request: is used for caching.
        parcel_id: Parcel's UUID.
        db: Active database session.
        session_id: Current session identifier.

    Returns:
        ParcelRead: Parcel data if found and owned by the session.

    Raises:
        HTTPException 404: If parcel does not exist or is unauthorized.
    """
    log.info("api_get_parcel_called: parcel_id=%s session_id=%s", parcel_id, session_id)
    try:
        parcel = await ParcelService(db).get_owned(parcel_id, session_id)
    except UnauthorizedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return parcel
