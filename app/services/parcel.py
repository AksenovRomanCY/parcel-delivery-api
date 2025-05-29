import logging
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessError, NotFoundError, UnauthorizedError
from app.models.parcel import Parcel
from app.models.parcel_type import ParcelType
from app.schemas import ParcelCreate, ParcelFilterParams
from app.services.base import CRUDBase

log = logging.getLogger(__name__)


class ParcelService(CRUDBase[Parcel]):
    """Business-logic facade for CRUD operations on ``Parcel``."""

    # Concrete SQLAlchemy model
    model = Parcel

    async def create_from_dto(self, data: ParcelCreate, session_id: str) -> Parcel:
        """Create and persist a new parcel from a validated DTO.

        Args:
            data: Incoming API payload mapped to ``ParcelCreate``.
            session_id: Session identifier that groups parcels belonging
                to the same (anonymous) user.

        Returns:
            Parcel: The newly created parcel, refreshed from the database.

        Raises:
            BusinessError: If ``data.weight_kg`` is not strictly positive.
        """
        # Check that parcel type exist
        type_exists = await self.session.scalar(
            select(ParcelType.id).where(ParcelType.id == data.parcel_type_id)
        )
        if not type_exists:
            log.warning("unknown_parcel_type: parcel_type_id=%s", data.parcel_type_id)
            raise BusinessError("Unknown parcel type")

        # Application-level check that complements any DB constraint.
        if data.weight_kg <= 0:
            raise BusinessError("Weight must be positive")

        parcel = Parcel(
            name=data.name,
            weight_kg=data.weight_kg,
            declared_value_usd=float(data.declared_value_usd),
            parcel_type_id=data.parcel_type_id,
            session_id=session_id,
        )

        await self._commit(parcel)

        log.info("parcel_created: parcel=%s, session_id=%s", parcel.id, session_id)
        return parcel

    async def get_owned(self, parcel_id: str, session_id: str) -> Parcel:
        """Fetch a parcel and verify that it belongs to the caller's session.

        Args:
            parcel_id: Primary key of the parcel.
            session_id: Caller’s session identifier.

        Returns:
            Parcel: The requested parcel instance.

        Raises:
            NotFoundError: If the parcel does not exist or belongs to a
                different session.
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

        if parcel.session_id != session_id:
            log.warning(
                "unauthorized_access: parcel_id=%s, session_id=%s",
                parcel_id,
                session_id,
            )
            raise UnauthorizedError("Parcel not found")

        return parcel

    async def list_owned(
        self,
        session_id: str,
        filters: ParcelFilterParams,
        limit: int,
        offset: int,
    ) -> tuple[int, list[Parcel]]:
        """Return a page of parcels owned by the session, with optional filters.

        Args:
            session_id: Session identifier used to scope the query.
            filters: Optional type and cost filters requested by the API.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip (for pagination).

        Returns:
            tuple[int, list[Parcel]]: ``(total_count, rows)``, where
            ``total_count`` is the number of matching rows and
            ``rows`` is the current page.
        """
        # Dynamically compose WHERE clauses.
        conditions = [Parcel.session_id == session_id]
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

        # Fast COUNT(*) via subquery to avoid re-executing the filter logic.
        total = await self.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )

        # Apply pagination.
        rows = await self.session.scalars(
            stmt.order_by(Parcel.id).limit(limit).offset(offset)
        )
        return int(total or 0), list(rows.all())

    async def set_delivery_cost(self, parcel: Parcel, cost_rub: Decimal) -> None:
        """Persist the delivery cost calculated for a parcel.

        Args:
            parcel: ORM instance to update (must already be persistent).
            cost_rub: Final delivery cost in rubles (high-precision decimal).

        Returns:
            None
        """
        # The column is defined as Float; convert explicitly.
        parcel.delivery_cost_rub = float(cost_rub)
        await self._commit(parcel)
