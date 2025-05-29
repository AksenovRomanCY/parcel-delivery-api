from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParcelType(Base):
    """Reference table for classifying parcels by type.

    Examples: "clothes", "electronics", "misc".

    This model is typically used for UI dropdowns and filtering.
    """

    __tablename__ = "parcel_type"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        unique=True,
        nullable=False,
        doc="Globally unique ID (UUIDv4) for the parcel type.",
    )

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        doc="Canonical name of the parcel type (e.g. 'clothes').",
    )
