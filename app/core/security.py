"""JWT, refresh-token, CSRF, and password hashing utilities."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from app.core.settings import DEFAULT_JWT_SECRET_KEY, settings

DEFAULT_USER_ROLE = "user"
DEFAULT_USER_SCOPES = ("parcels:read", "parcels:write")


@dataclass(frozen=True)
class TokenClaims:
    """Validated access-token claims used by request dependencies."""

    sub: str
    jti: str
    iss: str
    aud: str
    role: str
    scopes: tuple[str, ...]


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


def validate_jwt_secret() -> None:
    """Fail production startup when the configured JWT secret is unsafe."""
    if settings.ENVIRONMENT != "prod":
        return

    if settings.JWT_SECRET_KEY == DEFAULT_JWT_SECRET_KEY:
        msg = "JWT_SECRET_KEY must be changed in production"
        raise RuntimeError(msg)

    if len(settings.JWT_SECRET_KEY) < 32:
        msg = "JWT_SECRET_KEY must be at least 32 characters in production"
        raise RuntimeError(msg)


def hash_token(token: str) -> str:
    """Return a stable SHA-256 hash for a bearer/refresh token."""
    return sha256(token.encode()).hexdigest()


def create_refresh_token() -> tuple[str, str]:
    """Create a raw refresh token and its server-side JTI."""
    jti = str(uuid4())
    raw_token = token_urlsafe(48)
    return raw_token, jti


def create_csrf_token() -> str:
    """Create the readable CSRF token paired with the refresh cookie."""
    return token_urlsafe(32)


def create_access_token(
    subject: str,
    *,
    role: str = DEFAULT_USER_ROLE,
    scopes: Sequence[str] = DEFAULT_USER_SCOPES,
) -> str:
    """Create a JWT access token with the given subject claim.

    Args:
        subject: User identifier stored in the JWT ``sub`` claim.
        role: Role claim to include in the access token.
        scopes: Space-delimited permission scopes to include in the token.

    Returns:
        Signed JWT access token accepted by ``get_current_user_id``.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MIN)
    token: str = jwt.encode(
        {
            "sub": subject,
            "exp": expire,
            "iat": now,
            "nbf": now,
            "jti": str(uuid4()),
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "role": role,
            "scope": " ".join(scopes),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def decode_token(
    token: str,
    *,
    required_scopes: Iterable[str] = (),
) -> TokenClaims | None:
    """Decode and validate a JWT token, returning typed claims or None.

    Invalid signatures, unsupported algorithms, expired tokens, issuer/audience
    mismatches, missing claims, and missing scopes all collapse to ``None`` so
    route dependencies can return one consistent auth error.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        sub = payload.get("sub")
        jti = payload.get("jti")
        iss = payload.get("iss")
        aud = payload.get("aud")
        role = payload.get("role")
        scope_value = payload.get("scope", "")
        if (
            not isinstance(sub, str)
            or not isinstance(jti, str)
            or not isinstance(iss, str)
            or not isinstance(aud, str)
            or not isinstance(role, str)
            or not isinstance(scope_value, str)
        ):
            return None

        scopes = tuple(scope_value.split())
        if not set(required_scopes).issubset(scopes):
            return None

        return TokenClaims(
            sub=sub,
            jti=jti,
            iss=iss,
            aud=aud,
            role=role,
            scopes=scopes,
        )
    except jwt.PyJWTError:
        return None
