"""Integration tests for rate limiting."""

from collections.abc import Callable

from httpx import AsyncClient

ParcelPayloadFactory = Callable[..., dict[str, object]]
AuthContext = tuple[dict[str, str], str]


async def test_rate_limit_post_parcels_returns_429(
    client: AsyncClient,
    auth_context: AuthContext,
    parcel_type_id: str,
    parcel_payload_factory: ParcelPayloadFactory,
) -> None:
    """POST /parcels should return 429 after exceeding the rate limit."""
    # Arrange
    body = parcel_payload_factory(
        parcel_type_id,
        name="Rate Test",
        weight_kg="1.000",
        declared_value_usd="10.00",
    )
    headers, _user_id = auth_context

    # Act
    for _ in range(20):
        resp = await client.post("/parcels", json=body, headers=headers)
        assert resp.status_code == 201
    resp = await client.post("/parcels", json=body, headers=headers)

    # Assert
    assert resp.status_code == 429


async def test_recalc_requires_admin_token(
    client: AsyncClient,
    enable_task_admin_token: None,
) -> None:
    """POST /tasks/recalc-delivery should reject callers without ops token."""
    # Arrange

    # Act
    resp = await client.post("/tasks/recalc-delivery")

    # Assert
    assert resp.status_code == 403


async def test_rate_limit_recalc_returns_429(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """POST /tasks/recalc-delivery should return 429 after 5 requests."""
    # Arrange
    headers = admin_headers

    # Act
    for _ in range(5):
        resp = await client.post("/tasks/recalc-delivery", headers=headers)
        assert resp.status_code == 202
    resp = await client.post("/tasks/recalc-delivery", headers=headers)

    # Assert
    assert resp.status_code == 429


async def test_rate_limit_independent_endpoints(
    client: AsyncClient,
    auth_context: AuthContext,
    admin_headers: dict[str, str],
) -> None:
    """Rate limits on one endpoint do not affect another."""
    # Arrange
    auth_headers, _user_id = auth_context
    for _ in range(5):
        await client.post("/tasks/recalc-delivery", headers=admin_headers)

    # Act
    resp = await client.get("/parcels", headers=auth_headers)

    # Assert
    assert resp.status_code == 200
