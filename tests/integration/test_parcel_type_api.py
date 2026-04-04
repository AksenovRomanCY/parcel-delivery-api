SEEDED_NAMES = {"clothes", "electronics", "misc"}


async def test_list_parcel_types(client):
    resp = await client.get("/parcel-types")
    assert resp.status_code == 200
    data = resp.json()
    names = {item["name"] for item in data["items"]}
    assert SEEDED_NAMES.issubset(names)


async def test_parcel_types_pagination(client):
    resp = await client.get("/parcel-types?limit=1&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["limit"] == 1


async def test_parcel_type_structure(client):
    resp = await client.get("/parcel-types")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert isinstance(item["id"], str)
        assert isinstance(item["name"], str)
        assert set(item.keys()) == {"id", "name"}
