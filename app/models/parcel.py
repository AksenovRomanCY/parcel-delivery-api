from decimal import Decimal
from uuid import uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
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
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="ck_parcel_weight_positive"),
        CheckConstraint("declared_value_usd >= 0", name="ck_parcel_value_non_negative"),
        CheckConstraint(
            "delivery_cost_rub >= 0 OR delivery_cost_rub IS NULL",
            name="ck_parcel_cost_non_negative",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )

    declared_value_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    delivery_cost_rub: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    parcel_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("parcel_type.id"),
        nullable=False,
    )

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=True,
    )

    parcel_type: Mapped[ParcelType] = relationship(
        backref="parcels",
    )
