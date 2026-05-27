"""Integration tests for legacy session middleware."""

from collections.abc import Callable
from uuid import UUID, uuid4

from httpx import AsyncClient

SESSION_HEADER = "X-Session-Id"
ParcelPayloadFactory = Callable[..., dict[str, object]]


async def test_no_session_header_generates_uuid(client: AsyncClient) -> None:
    """Missing session header should generate a UUID response header."""
    # Arrange

    # Act
    resp = await client.get("/health")

    # Assert
    assert resp.status_code == 200
    session = resp.headers.get(SESSION_HEADER)
    assert session is not None
    UUID(session)


async def test_valid_session_header_preserved(client: AsyncClient) -> None:
    """Valid session header should be echoed back unchanged."""
    # Arrange
    sid = str(uuid4())

    # Act
    resp = await client.get("/health", headers={SESSION_HEADER: sid})

    # Assert
    assert resp.headers[SESSION_HEADER] == sid


async def test_invalid_session_header_replaced(client: AsyncClient) -> None:
    """Invalid session header should be replaced with a valid UUID."""
    # Arrange
    headers = {SESSION_HEADER: "not-a-uuid"}

    # Act
    resp = await client.get("/health", headers=headers)

    # Assert
    returned = resp.headers[SESSION_HEADER]
    assert returned != "not-a-uuid"
    UUID(returned)


async def test_post_parcel_session_consistency(
    client: AsyncClient,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """Parcel creation should use and echo the active session ID."""
    # Arrange
    sid = str(uuid4())
    headers = {SESSION_HEADER: sid}
    payload = parcel_payload_factory(
        parcel_type_id,
        name="Session Test",
        weight_kg="2.000",
        declared_value_usd="50.00",
    )

    # Act
    resp = await client.post("/parcels", json=payload, headers=headers)

    # Assert
    assert resp.status_code == 201
    assert resp.json()["owner_id"] == sid
    assert resp.headers[SESSION_HEADER] == sid
