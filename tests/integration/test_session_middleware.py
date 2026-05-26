"""Integration tests for legacy session middleware."""

from uuid import UUID, uuid4

from httpx import AsyncClient

SESSION_HEADER = "X-Session-Id"


async def test_no_session_header_generates_uuid(client: AsyncClient) -> None:
    """Missing session header should generate a UUID response header."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    session = resp.headers.get(SESSION_HEADER)
    assert session is not None
    UUID(session)  # raises if not valid UUID


async def test_valid_session_header_preserved(client: AsyncClient) -> None:
    """Valid session header should be echoed back unchanged."""
    sid = str(uuid4())
    resp = await client.get("/health", headers={SESSION_HEADER: sid})
    assert resp.headers[SESSION_HEADER] == sid


async def test_invalid_session_header_replaced(client: AsyncClient) -> None:
    """Invalid session header should be replaced with a valid UUID."""
    resp = await client.get("/health", headers={SESSION_HEADER: "not-a-uuid"})
    returned = resp.headers[SESSION_HEADER]
    assert returned != "not-a-uuid"
    UUID(returned)  # must be a valid UUID


async def test_post_parcel_session_consistency(
    client: AsyncClient, parcel_type_id: str
) -> None:
    """Parcel creation should use and echo the active session ID."""
    sid = str(uuid4())
    resp = await client.post(
        "/parcels",
        json={
            "name": "Session Test",
            "weightKg": "2.000",
            "declaredValueUsd": "50.00",
            "parcelTypeId": parcel_type_id,
        },
        headers={SESSION_HEADER: sid},
    )
    assert resp.status_code == 201
    assert resp.json()["owner_id"] == sid
    assert resp.headers[SESSION_HEADER] == sid
