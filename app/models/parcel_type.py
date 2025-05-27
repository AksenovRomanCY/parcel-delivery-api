from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParcelType(Base):
    __tablename__ = "parcel_type"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
