"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


async def test_register_success(isolated_client: AsyncClient) -> None:
    """Register a new user and receive a bearer token."""
    # Arrange
    client = isolated_client
    payload = {"email": "new@example.com", "password": "securepass123"}

    # Act
    resp = await client.post("/auth/register", json=payload)

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in resp.cookies
    assert "refresh_csrf" in resp.cookies


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


async def test_login_success(isolated_client: AsyncClient) -> None:
    """Authenticate an existing user and return a bearer token."""
    # Arrange
    client = isolated_client
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
    assert "refresh_token" in resp.cookies
    assert "refresh_csrf" in resp.cookies


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


async def test_refresh_rotates_cookie_token(isolated_client: AsyncClient) -> None:
    """Refresh should return a new access token and rotate cookies."""
    # Arrange
    client = isolated_client
    register_resp = await client.post(
        "/auth/register",
        json={"email": "refresh@example.com", "password": "securepass123"},
    )
    assert register_resp.status_code == 201
    old_refresh = client.cookies["refresh_token"]
    csrf = client.cookies["refresh_csrf"]

    # Act
    refresh_resp = await client.post("/auth/refresh", headers={"X-CSRF-Token": csrf})

    # Assert
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()
    assert client.cookies["refresh_token"] != old_refresh
    assert "refresh_csrf" in client.cookies


async def test_refresh_rejects_reused_token(isolated_client: AsyncClient) -> None:
    """Reusing an already rotated refresh token should be rejected."""
    # Arrange
    client = isolated_client
    register_resp = await client.post(
        "/auth/register",
        json={"email": "reuse@example.com", "password": "securepass123"},
    )
    assert register_resp.status_code == 201
    old_refresh = client.cookies["refresh_token"]
    old_csrf = client.cookies["refresh_csrf"]
    first_refresh = await client.post(
        "/auth/refresh",
        headers={"X-CSRF-Token": old_csrf},
    )
    assert first_refresh.status_code == 200
    client.cookies.set("refresh_token", old_refresh, domain="test.local", path="/auth")
    client.cookies.set("refresh_csrf", old_csrf, domain="test.local", path="/auth")

    # Act
    reuse_resp = await client.post("/auth/refresh", headers={"X-CSRF-Token": old_csrf})

    # Assert
    assert reuse_resp.status_code == 401


async def test_refresh_rejects_missing_csrf(isolated_client: AsyncClient) -> None:
    """Refresh should require the double-submit CSRF header."""
    # Arrange
    client = isolated_client
    register_resp = await client.post(
        "/auth/register",
        json={"email": "csrf@example.com", "password": "securepass123"},
    )
    assert register_resp.status_code == 201

    # Act
    resp = await client.post("/auth/refresh")

    # Assert
    assert resp.status_code == 403


async def test_logout_clears_cookies_and_blocks_refresh(
    isolated_client: AsyncClient,
) -> None:
    """Logout should revoke the current refresh token and clear cookies."""
    # Arrange
    client = isolated_client
    register_resp = await client.post(
        "/auth/register",
        json={"email": "logout@example.com", "password": "securepass123"},
    )
    assert register_resp.status_code == 201
    refresh_token = client.cookies["refresh_token"]
    csrf = client.cookies["refresh_csrf"]

    # Act
    logout_resp = await client.post("/auth/logout", headers={"X-CSRF-Token": csrf})

    # Assert
    assert logout_resp.status_code == 204
    assert "refresh_token" not in client.cookies
    assert "refresh_csrf" not in client.cookies

    client.cookies.set("refresh_token", refresh_token)
    client.cookies.set("refresh_csrf", csrf)
    refresh_resp = await client.post("/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert refresh_resp.status_code == 401


async def test_logout_all_revokes_all_user_refresh_tokens(
    isolated_client: AsyncClient,
) -> None:
    """Logout-all should revoke every refresh token for the authenticated user."""
    # Arrange
    client = isolated_client
    email = "logout-all@example.com"
    password = "securepass123"
    register_resp = await client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_resp.status_code == 201
    first_refresh = client.cookies["refresh_token"]
    first_csrf = client.cookies["refresh_csrf"]
    login_resp = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    # Act
    logout_all_resp = await client.post(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Assert
    assert logout_all_resp.status_code == 204
    client.cookies.set("refresh_token", first_refresh)
    client.cookies.set("refresh_csrf", first_csrf)
    refresh_resp = await client.post(
        "/auth/refresh",
        headers={"X-CSRF-Token": first_csrf},
    )
    assert refresh_resp.status_code == 401
