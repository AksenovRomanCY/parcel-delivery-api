from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session_id
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
    parcel = await ParcelService(db).create_from_dto(body, session_id)
    return {"id": parcel.id, "session_id": session_id}


# GET /parcels
@router.get(
    "",
    response_model=PaginatedResponse[ParcelRead],
    status_code=status.HTTP_200_OK,
)
async def list_parcels(
    pagination: PaginationParams = Depends(),
    filters: ParcelFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """List parcels belonging to the current session, with optional filters.

    Supports pagination and filtering by parcel type and delivery-cost
    presence.

    Args:
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
async def get_parcel(
    parcel_id: str,
    db: AsyncSession = Depends(get_db),
    session_id: str = Depends(get_session_id),
):
    """Retrieve a single parcel by ID, ensuring it belongs to the session.

    Args:
        parcel_id: Parcel's UUID.
        db: Active database session.
        session_id: Current session identifier.

    Returns:
        ParcelRead: Parcel data if found and owned by the session.

    Raises:
        HTTPException 404: If parcel does not exist or is unauthorized.
    """
    parcel = await ParcelService(db).get_owned(parcel_id, session_id)
    return parcel
