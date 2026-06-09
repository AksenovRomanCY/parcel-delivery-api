"""Integration tests for legacy session middleware."""

from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middlewares.session import assign_session_id

SESSION_HEADER = "X-Session-Id"


def _legacy_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(assign_session_id)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _legacy_client() -> AsyncClient:
    transport = ASGITransport(app=_legacy_app())
    return AsyncClient(transport=transport, base_url="http://test")


async def test_no_session_header_generates_uuid() -> None:
    """Missing session header should generate a UUID response header."""
    # Arrange

    # Act
    async with _legacy_client() as client:
        resp = await client.get("/health")

    # Assert
    assert resp.status_code == 200
    session = resp.headers.get(SESSION_HEADER)
    assert session is not None
    UUID(session)
    assert resp.headers["Deprecation"] == "true"
    assert "Sunset" in resp.headers


async def test_valid_session_header_preserved() -> None:
    """Valid session header should be echoed back unchanged."""
    # Arrange
    sid = str(uuid4())

    # Act
    async with _legacy_client() as client:
        resp = await client.get("/health", headers={SESSION_HEADER: sid})

    # Assert
    assert resp.headers[SESSION_HEADER] == sid


async def test_invalid_session_header_replaced() -> None:
    """Invalid session header should be replaced with a valid UUID."""
    # Arrange
    headers = {SESSION_HEADER: "not-a-uuid"}

    # Act
    async with _legacy_client() as client:
        resp = await client.get("/health", headers=headers)

    # Assert
    returned = resp.headers[SESSION_HEADER]
    assert returned != "not-a-uuid"
    UUID(returned)
