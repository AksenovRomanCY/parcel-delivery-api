"""Integration tests for parcel endpoints."""

from collections.abc import Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient

SESSION_HEADER = "X-Session-Id"
ParcelPayloadFactory = Callable[..., dict[str, object]]


async def test_create_parcel(
    client: AsyncClient,
    session_id: str,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel creation should return an ID and the effective owner ID."""
    # Arrange
    payload = parcel_payload_factory(parcel_type_id)
    headers = {SESSION_HEADER: session_id}

    # Act
    resp = await client.post("/parcels", json=payload, headers=headers)

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["owner_id"] == session_id


async def test_create_parcel_empty_body(client: AsyncClient, session_id: str) -> None:
    """Parcel creation should validate required body fields."""
    # Arrange
    headers = {SESSION_HEADER: session_id}

    # Act
    resp = await client.post("/parcels", json={}, headers=headers)

    # Assert
    assert resp.status_code == 422


async def test_create_parcel_invalid_type(
    client: AsyncClient,
    session_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel creation should reject unknown parcel types."""
    # Arrange
    payload = parcel_payload_factory(str(uuid4()))
    headers = {SESSION_HEADER: session_id}

    # Act
    resp = await client.post("/parcels", json=payload, headers=headers)

    # Assert
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == "business_error"
    assert "Unknown parcel type" in data["message"]


async def test_create_parcel_negative_weight(
    client: AsyncClient,
    session_id: str,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel creation should reject negative weight."""
    # Arrange
    payload = parcel_payload_factory(parcel_type_id, weight_kg="-1")
    headers = {SESSION_HEADER: session_id}

    # Act
    resp = await client.post("/parcels", json=payload, headers=headers)

    # Assert
    assert resp.status_code == 422


async def test_list_own_parcels(
    client: AsyncClient,
    session_id: str,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel list should return parcels owned by the active session."""
    # Arrange
    headers = {SESSION_HEADER: session_id}
    create_resp = await client.post(
        "/parcels",
        json=parcel_payload_factory(parcel_type_id),
        headers=headers,
    )
    assert create_resp.status_code == 201

    # Act
    list_resp = await client.get("/parcels", headers=headers)

    # Assert
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    ids = [p["id"] for p in data["items"]]
    assert create_resp.json()["id"] in ids


async def test_list_parcels_pagination(
    client: AsyncClient,
    session_id: str,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel list should honor limit and offset."""
    # Arrange
    headers = {SESSION_HEADER: session_id}
    for index in range(2):
        resp = await client.post(
            "/parcels",
            json=parcel_payload_factory(parcel_type_id, name=f"Parcel {index}"),
            headers=headers,
        )
        assert resp.status_code == 201

    # Act
    list_resp = await client.get(
        "/parcels?limit=1&offset=1",
        headers=headers,
    )

    # Assert
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data["items"]) == 1
    assert data["total"] >= 2
    assert data["limit"] == 1
    assert data["offset"] == 1


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
async def test_list_parcels_rejects_invalid_pagination(
    client: AsyncClient,
    session_id: str,
    query: str,
) -> None:
    """Parcel list should reject invalid pagination boundaries."""
    # Arrange
    headers = {SESSION_HEADER: session_id}

    # Act
    resp = await client.get(f"/parcels?{query}", headers=headers)

    # Assert
    assert resp.status_code == 422


async def test_get_parcel_by_id(
    client: AsyncClient,
    session_id: str,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel detail should return an owned parcel by ID."""
    # Arrange
    headers = {SESSION_HEADER: session_id}
    create_resp = await client.post(
        "/parcels",
        json=parcel_payload_factory(parcel_type_id, name="Specific Parcel"),
        headers=headers,
    )
    parcel_id = create_resp.json()["id"]

    # Act
    get_resp = await client.get(f"/parcels/{parcel_id}", headers=headers)

    # Assert
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == parcel_id
    assert data["name"] == "Specific Parcel"


async def test_get_parcel_forbidden_other_session(
    client: AsyncClient,
    session_id: str,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel detail should reject access from another session."""
    # Arrange
    create_resp = await client.post(
        "/parcels",
        json=parcel_payload_factory(parcel_type_id),
        headers={SESSION_HEADER: session_id},
    )
    parcel_id = create_resp.json()["id"]
    other_headers = {SESSION_HEADER: str(uuid4())}

    # Act
    get_resp = await client.get(f"/parcels/{parcel_id}", headers=other_headers)

    # Assert
    assert get_resp.status_code == 403
    assert get_resp.json()["detail"] == "Forbidden"


async def test_get_parcel_not_found(client: AsyncClient, session_id: str) -> None:
    """Parcel detail should return 404 for a missing parcel."""
    # Arrange
    headers = {SESSION_HEADER: session_id}
    parcel_id = str(uuid4())

    # Act
    resp = await client.get(f"/parcels/{parcel_id}", headers=headers)

    # Assert
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Not found"
