from uuid import uuid4

SESSION_HEADER = "X-Session-Id"


def _parcel_body(parcel_type_id: str, **overrides) -> dict:
    """Build a valid parcel creation payload (camelCase)."""
    base = {
        "name": "Test Parcel",
        "weightKg": "1.500",
        "declaredValueUsd": "100.00",
        "parcelTypeId": parcel_type_id,
    }
    base.update(overrides)
    return base


async def test_create_parcel(client, session_id, parcel_type_id):
    resp = await client.post(
        "/parcels",
        json=_parcel_body(parcel_type_id),
        headers={SESSION_HEADER: session_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["session_id"] == session_id


async def test_create_parcel_empty_body(client, session_id):
    resp = await client.post(
        "/parcels",
        json={},
        headers={SESSION_HEADER: session_id},
    )
    assert resp.status_code == 422


async def test_create_parcel_invalid_type(client, session_id):
    resp = await client.post(
        "/parcels",
        json=_parcel_body(str(uuid4())),
        headers={SESSION_HEADER: session_id},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == "business_error"
    assert "Unknown parcel type" in data["message"]


async def test_create_parcel_negative_weight(client, session_id, parcel_type_id):
    resp = await client.post(
        "/parcels",
        json=_parcel_body(parcel_type_id, weightKg="-1"),
        headers={SESSION_HEADER: session_id},
    )
    assert resp.status_code == 422


async def test_list_own_parcels(client, session_id, parcel_type_id):
    # Create a parcel first
    create_resp = await client.post(
        "/parcels",
        json=_parcel_body(parcel_type_id),
        headers={SESSION_HEADER: session_id},
    )
    assert create_resp.status_code == 201

    # List parcels for the same session
    list_resp = await client.get(
        "/parcels",
        headers={SESSION_HEADER: session_id},
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    ids = [p["id"] for p in data["items"]]
    assert create_resp.json()["id"] in ids


async def test_list_parcels_pagination(client, session_id, parcel_type_id):
    # Create 2 parcels
    for _ in range(2):
        resp = await client.post(
            "/parcels",
            json=_parcel_body(parcel_type_id),
            headers={SESSION_HEADER: session_id},
        )
        assert resp.status_code == 201

    # Request page of size 1
    list_resp = await client.get(
        "/parcels?limit=1&offset=0",
        headers={SESSION_HEADER: session_id},
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data["items"]) == 1
    assert data["total"] >= 2
    assert data["limit"] == 1
    assert data["offset"] == 0


async def test_get_parcel_by_id(client, session_id, parcel_type_id):
    create_resp = await client.post(
        "/parcels",
        json=_parcel_body(parcel_type_id, name="Specific Parcel"),
        headers={SESSION_HEADER: session_id},
    )
    parcel_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/parcels/{parcel_id}",
        headers={SESSION_HEADER: session_id},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == parcel_id
    assert data["name"] == "Specific Parcel"


async def test_get_parcel_forbidden_other_session(client, session_id, parcel_type_id):
    # Create with session A
    create_resp = await client.post(
        "/parcels",
        json=_parcel_body(parcel_type_id),
        headers={SESSION_HEADER: session_id},
    )
    parcel_id = create_resp.json()["id"]

    # Access with session B
    other_session = str(uuid4())
    get_resp = await client.get(
        f"/parcels/{parcel_id}",
        headers={SESSION_HEADER: other_session},
    )
    assert get_resp.status_code == 403
    assert get_resp.json()["detail"] == "Forbidden"


async def test_get_parcel_not_found(client, session_id):
    resp = await client.get(
        f"/parcels/{uuid4()}",
        headers={SESSION_HEADER: session_id},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Not found"
