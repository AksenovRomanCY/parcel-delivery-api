"""Integration tests for health endpoint."""

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    """Health endpoint should return an ok status."""
    # Arrange

    # Act
    resp = await client.get("/health")

    # Assert
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
