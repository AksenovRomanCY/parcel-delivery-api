from typing import Iterable

from sqlalchemy import func, insert, select

from app.models.parcel_type import ParcelType
from app.services.base import CRUDBase


class ParcelTypeService(CRUDBase[ParcelType]):
    """Service layer that exposes CRUD-style helpers for ``ParcelType``."""

    # Concrete SQLAlchemy model
    model = ParcelType

    async def list_all(self) -> Iterable[ParcelType]:
        """Return every parcel type sorted alphabetically.

        Returns:
            Iterable[ParcelType]: All rows ordered by the ``name`` column.
        """
        # Compose the query once; ordering is pushed down to the database.
        stmt = select(ParcelType).order_by(ParcelType.name)

        # Fetch the data as ORM objects.
        res = await self.session.scalars(stmt)
        return res.all()

    async def total(self) -> int:
        """Return the total number of parcel-type rows in the database.

        Executes ``SELECT COUNT(*)`` against the model specified by the
        service and converts the result to ``int`` so that callers never
        receive ``None``.

        Returns:
            int: Row count, or ``0`` if the table is empty.
        """
        # Build a COUNT(*) statement on the target table.
        stmt = select(func.count()).select_from(self.model)

        # Execute the query and coerce ``None`` to zero.
        return int(await self.session.scalar(stmt) or 0)
