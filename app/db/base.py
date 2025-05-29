from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models with async support.

    Combines:
    - ``AsyncAttrs``: enables async methods like ``await instance.refresh()``.
    - ``DeclarativeBase``: base for ORM class declaration using SQLAlchemy 2.0+ style.

    All models in the application should inherit from this class.
    """

    pass
