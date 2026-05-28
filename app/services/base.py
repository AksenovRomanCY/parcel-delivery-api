"""Reusable SQLAlchemy query helpers for service classes.

The base class is intentionally small. Feature-specific services should add
business rules on top instead of pushing domain behavior into generic CRUD.
"""

from collections.abc import Iterable
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

ModelT = TypeVar("ModelT")


class CRUDBase(Generic[ModelT]):
    """Universal asynchronous CRUD layer for SQLAlchemy 2.0 models.

    Subclasses must assign the concrete ORM model class to the **class**
    attribute ``model``:

    ```python
    class UserCRUD(CRUDBase[User]):
        model = User
    ```

    The mix-in then provides coroutine helpers for common create / read
    operations while keeping the calling code free of SQLAlchemy details.
    """

    #: Concrete SQLAlchemy declarative model, injected by a subclass
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        """Create a CRUD helper bound to a given database session.

        Args:
            session: Live `AsyncSession` used for all database operations.
        """
        self.session = session

    async def _commit(self, *instances: ModelT) -> None:
        """Persist one or more ORM instances and refresh them.

        The objects are added to the session, `commit` is issued, and each
        instance is reloaded so that auto-generated fields (e.g. primary
        keys, defaults) become available.

        Args:
            *instances: Arbitrary collection of ORM objects to be saved.
        """
        # Stage instances for insertion/update and refresh them after commit so
        # callers can safely read generated IDs/defaults immediately.
        self.session.add_all(instances)
        await self.session.commit()
        for inst in instances:
            await self.session.refresh(inst)

    async def get(self, id_: str) -> ModelT | None:
        """Return a single row by primary key.

        Args:
            id_: Primary-key value expected by the target table.

        Returns:
            The matching ORM object or `None` if the row does not exist.
        """
        return await self.session.get(self.model, id_)

    async def list(self, *filters: InstrumentedAttribute[bool]) -> Iterable[ModelT]:
        """Fetch all rows that satisfy the given SQLAlchemy filter clauses.

        Args:
            *filters: Boolean SQL expressions created with model columns,
                e.g. ``User.is_active == True``. If omitted, all rows
                are returned.

        Returns:
            An iterable of ORM objects meeting the criteria.
        """
        # Keep the generic helper limited to simple WHERE clauses; services can
        # compose richer statements when they need joins, eager loading, or
        # pagination.
        stmt = select(self.model).where(*filters)
        result = await self.session.scalars(stmt)
        return result.all()

    async def create(self, obj: ModelT) -> ModelT:
        """Insert a new row and return the fully populated object.

        Args:
            obj: An instance of the target ORM model that has **not**
                yet been added to a session.

        Returns:
            The same object after it has been persisted and refreshed.
        """
        await self._commit(obj)
        return obj
