"""Integration tests for authentication endpoints."""


async def test_register_success(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client):
    email = "dup@example.com"
    payload = {"email": email, "password": "securepass123"}

    resp1 = await client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["message"]


async def test_register_weak_password(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert resp.status_code == 422


async def test_register_invalid_email(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "securepass123"},
    )
    assert resp.status_code == 422


async def test_login_success(client):
    email = "login@example.com"
    password = "securepass123"

    await client.post("/auth/register", json={"email": email, "password": password})

    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    email = "wrongpw@example.com"
    await client.post(
        "/auth/register",
        json={"email": email, "password": "securepass123"},
    )

    resp = await client.post(
        "/auth/login", json={"email": email, "password": "wrongpassword"}
    )
    assert resp.status_code == 401


async def test_login_nonexistent_user(client):
    resp = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 401
