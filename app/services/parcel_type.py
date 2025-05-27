from typing import Iterable

from sqlalchemy import select

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

    async def seed_defaults(self) -> None:
        """Populate the table with three default parcel types.

        The defaults are *clothes*, *electronics* and *misc*.
        Seeding runs only when the table is empty to avoid duplicates.

        Returns:
            None
        """
        # Short-circuit if at least one row already exists.
        if await self.session.scalar(select(ParcelType.id).limit(1)):
            return

        defaults = ("clothes", "electronics", "misc")

        # Bulk-add without committing after each insert.
        self.session.add_all(ParcelType(name=n) for n in defaults)

        # Commit once to persist all rows atomically.
        await self.session.commit()
