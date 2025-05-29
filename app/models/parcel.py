from uuid import uuid4

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.parcel_type import ParcelType


class Parcel(Base):
    """Parcel model representing a physical shipment unit.

    Stores weight, declared value, and session ownership. The delivery
    cost is computed asynchronously after creation. Each parcel is
    associated with a parcel type (e.g., "clothes", "electronics").
    """

    __tablename__ = "parcel"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
        doc="Globally unique ID (UUIDv4).",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable parcel name (e.g. 'Laptop bag').",
    )

    weight_kg: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Weight in kilograms, used for cost calculation.",
    )

    declared_value_usd: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Declared customs value in USD.",
    )

    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Anonymous session ID that owns this parcel.",
    )

    delivery_cost_rub: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Final delivery cost in RUB, calculated asynchronously.",
    )

    parcel_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("parcel_type.id"),
        nullable=False,
        doc="Foreign key to parcel type (e.g. electronics, misc).",
    )

    parcel_type: Mapped[ParcelType] = relationship(
        backref="parcels",
        doc="ORM relationship to the referenced ParcelType.",
    )
