"""Parcel-type API endpoints.

The router contains read-only operations for the reference table
:class:`app.models.parcel_type.ParcelType` and is mounted under the
``/parcel-types`` prefix.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.schemas import PaginatedResponse, PaginationParams, ParcelTypeRead
from app.services import ParcelTypeService

router = APIRouter(prefix="/parcel-types", tags=["parcel-types"])


@router.get(
    "",
    response_model=PaginatedResponse[ParcelTypeRead],
    status_code=status.HTTP_200_OK,
)
async def list_parcel_types(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of all available parcel types.

    The endpoint is intended for UI dropdowns and filter widgets that
    need to display human-readable parcel categories. Results are sorted
    alphabetically by the ``name`` column to provide a stable, user-
    friendly order.

    Args:
        pagination: Query parameters ``limit`` (1 – 100, default 20) and
            ``offset`` injected via :class:`PaginationParams`.
        db: Async SQLAlchemy session provided by the application
            dependency ``get_db``.

    Returns:
        PaginatedResponse[ParcelTypeRead]: An object that contains the
        current page of parcel types, the total row count, and the
        original pagination parameters.
    """
    svc = ParcelTypeService(db)

    # Total number of rows in the reference table.
    total = await svc.total()

    # Fetch all parcel types sorted by name (table is tiny).
    rows = await svc.list_all()

    # Client-requested slice; doing it in Python avoids an extra SQL query.
    sliced = rows[pagination.offset : pagination.offset + pagination.limit]

    return PaginatedResponse[ParcelTypeRead](
        items=sliced,
        total=int(total or 0),
        limit=pagination.limit,
        offset=pagination.offset,
    )
