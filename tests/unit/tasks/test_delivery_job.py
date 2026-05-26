"""Unit tests for delivery recalculation tasks."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.delivery import (  # noqa
    _acquire_lock,
    _fetch_unpriced,
    recalc_delivery_costs,
)


@pytest.mark.asyncio
@patch("app.tasks.delivery.get_redis")
async def test_acquire_lock_success(mock_get_redis: MagicMock) -> None:
    """Should acquire a Redis lock successfully if key does not exist."""
    redis_mock = AsyncMock()
    redis_mock.set.return_value = True
    mock_get_redis.return_value = redis_mock

    acquired = await _acquire_lock()
    assert acquired is True
    redis_mock.set.assert_called_once_with("delivery_job_lock", "1", ex=330, nx=True)


@pytest.mark.asyncio
async def test_fetch_unpriced() -> None:
    """Should return unpriced parcels fetched via SELECT with .is_(None)."""
    mock_session = AsyncMock(spec=AsyncSession)

    # simulate session.scalars returning an awaitable
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = ["parcel1", "parcel2"]

    mock_session.scalars.return_value = mock_scalars_result

    result = await _fetch_unpriced(mock_session)
    assert len(result) == 2

    mock_session.scalars.assert_called_once()
    mock_scalars_result.all.assert_called_once()


@pytest.mark.asyncio
@patch("app.tasks.delivery.DELIVERY_RECALC_PARCELS")
@patch("app.tasks.delivery.DELIVERY_RECALC_DURATION")
@patch("app.tasks.delivery._acquire_lock", return_value=True)
@patch("app.tasks.delivery.get_usd_rub_rate", return_value=Decimal("90.0"))
@patch("app.tasks.delivery._fetch_unpriced")
@patch("app.tasks.delivery.AsyncSessionLocal")
@patch("app.tasks.delivery.get_redis")
async def test_recalc_delivery_costs_updates(
    mock_get_redis: MagicMock,
    mock_session_local: MagicMock,
    mock_fetch_unpriced: MagicMock,
    mock_get_rate: MagicMock,  # noqa
    mock_acquire_lock: MagicMock,  # noqa
    mock_recalc_duration: MagicMock,
    mock_recalc_parcels: MagicMock,
) -> None:
    """Should recalculate delivery cost for unpriced parcels and persist them."""
    # Simulate one batch with one parcel
    mock_parcel = MagicMock(
        weight_kg=Decimal("2.000"), declared_value_usd=Decimal("100.00")
    )
    mock_fetch_unpriced.side_effect = [[mock_parcel], []]  # одна итерация
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    updated = await recalc_delivery_costs()
    assert updated == 1
    mock_session.commit.assert_called_once()
    mock_redis.set.assert_any_call("delivery_last_run_updated", "1")
    assert any(
        call.args[0] == "delivery_last_run_at" and "T" in call.args[1]
        for call in mock_redis.set.call_args_list
    )
    mock_recalc_duration.observe.assert_called_once()
    mock_recalc_parcels.inc.assert_called_once_with(1)
