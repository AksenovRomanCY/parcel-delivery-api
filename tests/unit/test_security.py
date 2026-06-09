"""Unit tests for JWT token and password hashing utilities."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    validate_jwt_secret,
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
    claims = decode_token(token)

    # Assert
    assert claims is not None
    assert claims.sub == subject
    assert claims.iss == settings.JWT_ISSUER
    assert claims.aud == settings.JWT_AUDIENCE
    assert claims.role == "user"
    assert set(claims.scopes) == {"parcels:read", "parcels:write"}


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


def test_decode_rejects_missing_scope() -> None:
    """JWT decoding should reject tokens without required scopes."""
    # Arrange
    token = create_access_token("user-123", scopes=("parcels:read",))

    # Act
    decoded = decode_token(token, required_scopes=("parcels:write",))

    # Assert
    assert decoded is None


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("iss", "wrong-issuer"),
        ("aud", "wrong-audience"),
    ],
)
def test_decode_rejects_wrong_issuer_or_audience(claim: str, value: str) -> None:
    """JWT decoding should validate issuer and audience claims."""
    # Arrange
    now = datetime.now(UTC)
    payload = {
        "sub": "user-123",
        "exp": now + timedelta(minutes=15),
        "iat": now,
        "nbf": now,
        "jti": "jti-123",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "role": "user",
        "scope": "parcels:read parcels:write",
        claim: value,
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    # Act
    decoded = decode_token(token)

    # Assert
    assert decoded is None


def test_validate_jwt_secret_rejects_default_in_prod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production startup should reject the default JWT secret."""
    # Arrange
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    monkeypatch.setattr(
        settings,
        "JWT_SECRET_KEY",
        "change-me-in-production-use-32-bytes-minimum",
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="changed in production"):
        validate_jwt_secret()


def test_validate_jwt_secret_allows_test_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-production environments may use local test secrets."""
    # Arrange
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "short")

    # Act
    validate_jwt_secret()

    # Assert
    # No exception is the assertion.
