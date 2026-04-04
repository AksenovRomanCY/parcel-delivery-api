from uuid import UUID, uuid4

SESSION_HEADER = "X-Session-Id"


async def test_no_session_header_generates_uuid(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    session = resp.headers.get(SESSION_HEADER)
    assert session is not None
    UUID(session)  # raises if not valid UUID


async def test_valid_session_header_preserved(client):
    sid = str(uuid4())
    resp = await client.get("/health", headers={SESSION_HEADER: sid})
    assert resp.headers[SESSION_HEADER] == sid


async def test_invalid_session_header_replaced(client):
    resp = await client.get("/health", headers={SESSION_HEADER: "not-a-uuid"})
    returned = resp.headers[SESSION_HEADER]
    assert returned != "not-a-uuid"
    UUID(returned)  # must be a valid UUID


async def test_post_parcel_session_consistency(client, parcel_type_id):
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
    assert resp.json()["session_id"] == sid
    assert resp.headers[SESSION_HEADER] == sid
