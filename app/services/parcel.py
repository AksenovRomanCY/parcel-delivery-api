import logging
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessError, NotFoundError, UnauthorizedError
from app.core.metrics import PARCELS_CREATED
from app.core.settings import settings
from app.models.parcel import Parcel
from app.models.parcel_type import ParcelType
from app.schemas import ParcelCreate, ParcelFilterParams
from app.services.base import CRUDBase

log = logging.getLogger(__name__)


class ParcelService(CRUDBase[Parcel]):
    """Business-logic facade for CRUD operations on ``Parcel``."""

    model = Parcel

    async def create_from_dto(self, data: ParcelCreate, owner_id: str) -> Parcel:
        """Create and persist a new parcel from a validated DTO.

        Args:
            data: Incoming API payload mapped to ``ParcelCreate``.
            owner_id: Session ID or user ID depending on AUTH_REQUIRED.

        Returns:
            Parcel: The newly created parcel, refreshed from the database.
        """
        type_exists = await self.session.scalar(
            select(ParcelType.id).where(ParcelType.id == data.parcel_type_id)
        )
        if not type_exists:
            log.warning("unknown_parcel_type: parcel_type_id=%s", data.parcel_type_id)
            raise BusinessError("Unknown parcel type")

        if data.weight_kg <= 0:
            raise BusinessError("Weight must be positive")

        parcel = Parcel(
            name=data.name,
            weight_kg=data.weight_kg,
            declared_value_usd=data.declared_value_usd,
            parcel_type_id=data.parcel_type_id,
            session_id=owner_id if not settings.AUTH_REQUIRED else "",
            user_id=owner_id if settings.AUTH_REQUIRED else None,
        )

        await self._commit(parcel)

        PARCELS_CREATED.labels(parcel_type=str(data.parcel_type_id)).inc()
        log.info("parcel_created: parcel=%s, owner_id=%s", parcel.id, owner_id)
        return parcel

    async def get_owned(self, parcel_id: str, owner_id: str) -> Parcel:
        """Fetch a parcel and verify that it belongs to the caller.

        Args:
            parcel_id: Primary key of the parcel.
            owner_id: Caller's session or user identifier.
        """
        stmt = (
            select(Parcel)
            .options(selectinload(Parcel.parcel_type))
            .where(Parcel.id == parcel_id)
        )
        parcel = await self.session.scalar(stmt)

        if parcel is None:
            log.warning("parcel_not_found: parcel_id=%s", parcel_id)
            raise NotFoundError("Parcel not found")

        if settings.AUTH_REQUIRED:
            owner_match = parcel.user_id == owner_id
        else:
            owner_match = parcel.session_id == owner_id

        if not owner_match:
            log.warning(
                "unauthorized_access: parcel_id=%s, owner_id=%s",
                parcel_id,
                owner_id,
            )
            raise UnauthorizedError("Parcel not found")

        return parcel

    async def list_owned(
        self,
        owner_id: str,
        filters: ParcelFilterParams,
        limit: int,
        offset: int,
    ) -> tuple[int, list[Parcel]]:
        """Return a page of parcels owned by the caller, with optional filters."""
        if settings.AUTH_REQUIRED:
            conditions = [Parcel.user_id == owner_id]
        else:
            conditions = [Parcel.session_id == owner_id]

        if filters.type_id:
            conditions.append(Parcel.parcel_type_id == filters.type_id)
        if filters.has_cost is True:
            conditions.append(Parcel.delivery_cost_rub.is_not(None))
        if filters.has_cost is False:
            conditions.append(Parcel.delivery_cost_rub.is_(None))

        stmt = (
            select(Parcel)
            .options(selectinload(Parcel.parcel_type))
            .where(and_(*conditions))
        )

        total = await self.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )

        rows = await self.session.scalars(
            stmt.order_by(Parcel.id).limit(limit).offset(offset)
        )
        return int(total or 0), list(rows.all())

    async def set_delivery_cost(self, parcel: Parcel, cost_rub: Decimal) -> None:
        """Persist the delivery cost calculated for a parcel."""
        parcel.delivery_cost_rub = cost_rub
        await self._commit(parcel)
