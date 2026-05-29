"""JWT token management and password hashing utilities."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.settings import settings


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: Raw password received from a validated request schema.

    Returns:
        Encoded bcrypt hash safe to store in the database.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Args:
        plain: Password supplied by the login request.
        hashed: Stored bcrypt hash from the user row.

    Returns:
        True when the password matches, otherwise False.
    """
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str) -> str:
    """Create a JWT access token with the given subject claim.

    Args:
        subject: User identifier stored in the JWT ``sub`` claim.

    Returns:
        Signed JWT access token accepted by ``get_current_user_id``.
    """
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MIN)
    token: str = jwt.encode(
        {"sub": subject, "exp": expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def decode_token(token: str) -> str | None:
    """Decode a JWT token and return the subject claim, or None if invalid.

    Invalid signatures, unsupported algorithms, and expired tokens all collapse
    to ``None`` so route dependencies can return one consistent auth error.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub: str | None = payload.get("sub")
        return sub
    except jwt.PyJWTError:
        return None
