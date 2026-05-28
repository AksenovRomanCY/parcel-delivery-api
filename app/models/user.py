"""User ORM model for JWT authentication mode.

Users are only required when ``AUTH_REQUIRED=True``. The legacy session mode can
still run without user accounts, which is why parcel ownership supports both
``session_id`` and nullable ``user_id``.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Registered user with email/password credentials.

    Passwords are stored as bcrypt hashes produced by ``app.core.security``.
    The model intentionally keeps only fields needed for authentication.
    """

    __tablename__ = "user"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
