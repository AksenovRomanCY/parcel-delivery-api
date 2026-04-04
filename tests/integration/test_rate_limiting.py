"""Integration tests for rate limiting."""

SESSION_HEADER = "X-Session-Id"


async def test_rate_limit_post_parcels_returns_429(client, session_id, parcel_type_id):
    """POST /parcels should return 429 after exceeding the rate limit."""
    body = {
        "name": "Rate Test",
        "weightKg": "1.000",
        "declaredValueUsd": "10.00",
        "parcelTypeId": parcel_type_id,
    }
    headers = {SESSION_HEADER: session_id}

    # Send 20 requests (the limit)
    for _ in range(20):
        resp = await client.post("/parcels", json=body, headers=headers)
        assert resp.status_code == 201

    # 21st request should be rate limited
    resp = await client.post("/parcels", json=body, headers=headers)
    assert resp.status_code == 429


async def test_rate_limit_recalc_returns_429(client, session_id):
    """POST /tasks/recalc-delivery should return 429 after 5 requests."""
    headers = {SESSION_HEADER: session_id}

    for _ in range(5):
        resp = await client.post("/tasks/recalc-delivery", headers=headers)
        assert resp.status_code == 202

    resp = await client.post("/tasks/recalc-delivery", headers=headers)
    assert resp.status_code == 429


async def test_rate_limit_independent_endpoints(client, session_id, parcel_type_id):
    """Rate limits on one endpoint do not affect another."""
    headers = {SESSION_HEADER: session_id}

    # Hit recalc 5 times to exhaust its limit
    for _ in range(5):
        await client.post("/tasks/recalc-delivery", headers=headers)

    # GET /parcels should still work (different limiter)
    resp = await client.get("/parcels", headers=headers)
    assert resp.status_code == 200
