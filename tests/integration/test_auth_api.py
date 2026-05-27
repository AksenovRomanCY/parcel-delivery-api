"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


async def test_register_success(client: AsyncClient) -> None:
    """Register a new user and receive a bearer token."""
    # Arrange
    payload = {"email": "new@example.com", "password": "securepass123"}

    # Act
    resp = await client.post("/auth/register", json=payload)

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client: AsyncClient) -> None:
    """Reject registration when the email is already present."""
    # Arrange
    email = "dup@example.com"
    payload = {"email": email, "password": "securepass123"}
    resp1 = await client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    # Act
    resp2 = await client.post("/auth/register", json=payload)

    # Assert
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["message"]


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "weak@example.com", "password": "short"},
        {"email": "not-an-email", "password": "securepass123"},
    ],
)
async def test_register_rejects_invalid_payloads(
    client: AsyncClient,
    payload: dict[str, str],
) -> None:
    """Reject registration payloads that fail schema validation."""
    # Arrange

    # Act
    resp = await client.post("/auth/register", json=payload)

    # Assert
    assert resp.status_code == 422


async def test_login_success(client: AsyncClient) -> None:
    """Authenticate an existing user and return a bearer token."""
    # Arrange
    email = "login@example.com"
    password = "securepass123"
    await client.post("/auth/register", json={"email": email, "password": password})

    # Act
    resp = await client.post("/auth/login", json={"email": email, "password": password})

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient) -> None:
    """Reject login when the password does not match."""
    # Arrange
    email = "wrongpw@example.com"
    await client.post(
        "/auth/register",
        json={"email": email, "password": "securepass123"},
    )

    # Act
    resp = await client.post(
        "/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )

    # Assert
    assert resp.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """Reject login for an email that has no account."""
    # Arrange
    payload = {"email": "nobody@example.com", "password": "securepass123"}

    # Act
    resp = await client.post("/auth/login", json=payload)

    # Assert
    assert resp.status_code == 401
