"""Unit tests for JWT token and password hashing utilities."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.settings import settings


def test_hash_and_verify_password() -> None:
    """Password hashing should verify the original password."""
    # Arrange
    password = "my-secret-password"

    # Act
    hashed = hash_password(password)

    # Assert
    assert hashed != password
    assert verify_password(password, hashed)


def test_verify_wrong_password() -> None:
    """Password verification should reject a wrong password."""
    # Arrange
    hashed = hash_password("correct-password")

    # Act
    verified = verify_password("wrong-password", hashed)

    # Assert
    assert not verified


def test_create_and_decode_token() -> None:
    """JWT creation and decoding should round-trip the subject."""
    # Arrange
    subject = "user-123"

    # Act
    token = create_access_token(subject)
    decoded = decode_token(token)

    # Assert
    assert decoded == subject


@pytest.mark.parametrize(
    "token",
    [
        jwt.encode(
            {"sub": "user-123", "exp": datetime.now(UTC) - timedelta(minutes=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        ),
        "not-a-valid-token",
        jwt.encode(
            {"sub": "user-123", "exp": datetime.now(UTC) + timedelta(hours=1)},
            "wrong-secret-key-use-32-bytes-minimum",
            algorithm=settings.JWT_ALGORITHM,
        ),
    ],
)
def test_decode_invalid_tokens(token: str) -> None:
    """Invalid JWTs should decode as invalid."""
    # Arrange

    # Act
    decoded = decode_token(token)

    # Assert
    assert decoded is None
