from uuid import uuid4

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.parcel_type import ParcelType


class Parcel(Base):
    __tablename__ = "parcel"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    declared_value_usd: Mapped[float] = mapped_column(Float, nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    delivery_cost_rub: Mapped[float | None] = mapped_column(Float, nullable=True)

    parcel_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parcel_type.id"), nullable=False
    )
    parcel_type: Mapped[ParcelType] = relationship(backref="parcels")
