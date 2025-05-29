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
async def test_acquire_lock_success(mock_get_redis):
    """Should acquire a Redis lock successfully if key does not exist."""
    redis_mock = AsyncMock()
    redis_mock.set.return_value = True
    mock_get_redis.return_value = redis_mock

    acquired = await _acquire_lock()
    assert acquired is True
    redis_mock.set.assert_called_once_with("delivery_job_lock", "1", ex=330, nx=True)


@pytest.mark.asyncio
async def test_fetch_unpriced():
    """Should return unpriced parcels fetched via SELECT with .is_(None)."""
    mock_session = AsyncMock(spec=AsyncSession)

    # simulate session.scalars returning an awaitable
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = ["parcel1", "parcel2"]

    mock_session.scalars.return_value = mock_scalars_result

    result = await _fetch_unpriced(mock_session)
    assert result == ["parcel1", "parcel2"]

    mock_session.scalars.assert_called_once()
    mock_scalars_result.all.assert_called_once()


@pytest.mark.asyncio
@patch("app.tasks.delivery._acquire_lock", return_value=True)
@patch("app.tasks.delivery.get_usd_rub_rate", return_value=Decimal("90.0"))
@patch("app.tasks.delivery._fetch_unpriced")
@patch("app.tasks.delivery.AsyncSessionLocal")
@patch("app.tasks.delivery.get_redis")
async def test_recalc_delivery_costs_updates(
    mock_get_redis,
    mock_session_local,
    mock_fetch_unpriced,
    mock_get_rate,  # noqa
    mock_acquire_lock,  # noqa
):
    """Should recalculate delivery cost for unpriced parcels and persist them."""
    # Simulate one batch with one parcel
    mock_parcel = MagicMock(weight_kg=2.0, declared_value_usd="100.0")
    mock_fetch_unpriced.side_effect = [[mock_parcel], []]  # одна итерация
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_redis = AsyncMock()
    mock_get_redis.return_value = mock_redis

    updated = await recalc_delivery_costs()
    assert updated == 1
    mock_session.commit.assert_called_once()
    mock_redis.set.assert_called_once_with("delivery_last_run_ts", "1")
