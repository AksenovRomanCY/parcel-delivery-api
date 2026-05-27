"""Integration tests for parcel-type endpoints."""

import pytest
from httpx import AsyncClient

SEEDED_NAMES = {"clothes", "electronics", "misc"}


async def test_list_parcel_types(client: AsyncClient) -> None:
    """Parcel-type list should include seeded reference rows."""
    # Arrange

    # Act
    resp = await client.get("/parcel-types")

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    names = {item["name"] for item in data["items"]}
    assert SEEDED_NAMES.issubset(names)


async def test_parcel_types_pagination(client: AsyncClient) -> None:
    """Parcel-type list should support pagination."""
    # Arrange

    # Act
    resp = await client.get("/parcel-types?limit=1&offset=1")

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["limit"] == 1
    assert data["offset"] == 1


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
async def test_parcel_types_reject_invalid_pagination(
    client: AsyncClient,
    query: str,
) -> None:
    """Parcel-type list should reject invalid pagination boundaries."""
    # Arrange

    # Act
    resp = await client.get(f"/parcel-types?{query}")

    # Assert
    assert resp.status_code == 422


async def test_parcel_type_structure(client: AsyncClient) -> None:
    """Parcel-type items should expose only public fields."""
    # Arrange

    # Act
    resp = await client.get("/parcel-types")

    # Assert
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert isinstance(item["id"], str)
        assert isinstance(item["name"], str)
        assert set(item.keys()) == {"id", "name"}
