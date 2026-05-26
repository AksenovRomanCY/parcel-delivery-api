"""Unit tests for JWT token and password hashing utilities."""

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.settings import settings


def test_hash_and_verify_password() -> None:
    """Password hashing should verify the original password."""
    password = "my-secret-password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_verify_wrong_password() -> None:
    """Password verification should reject a wrong password."""
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_create_and_decode_token() -> None:
    """JWT creation and decoding should round-trip the subject."""
    subject = "user-123"
    token = create_access_token(subject)
    decoded = decode_token(token)
    assert decoded == subject


def test_decode_expired_token() -> None:
    """Expired JWT should decode as invalid."""
    expire = datetime.now(UTC) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": "user-123", "exp": expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert decode_token(token) is None


def test_decode_invalid_token() -> None:
    """Malformed JWT should decode as invalid."""
    assert decode_token("not-a-valid-token") is None


def test_decode_token_wrong_secret() -> None:
    """JWT signed with the wrong secret should decode as invalid."""
    token = jwt.encode(
        {"sub": "user-123", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "wrong-secret-key",
        algorithm=settings.JWT_ALGORITHM,
    )
    assert decode_token(token) is None
