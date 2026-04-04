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


def test_hash_and_verify_password():
    password = "my-secret-password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_verify_wrong_password():
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_create_and_decode_token():
    subject = "user-123"
    token = create_access_token(subject)
    decoded = decode_token(token)
    assert decoded == subject


def test_decode_expired_token():
    expire = datetime.now(UTC) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": "user-123", "exp": expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert decode_token(token) is None


def test_decode_invalid_token():
    assert decode_token("not-a-valid-token") is None


def test_decode_token_wrong_secret():
    token = jwt.encode(
        {"sub": "user-123", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "wrong-secret-key",
        algorithm=settings.JWT_ALGORITHM,
    )
    assert decode_token(token) is None
