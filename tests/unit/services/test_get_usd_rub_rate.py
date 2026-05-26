"""Unit tests for the USD/RUB rate fetcher."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rates import (  # noqa
    CBR_URL,
    KEY_TMPL,
    _fetch_rate_from_cbr,
    get_usd_rub_rate,
)


@pytest.mark.asyncio
@patch("app.services.rates.get_redis")
async def test_get_usd_rub_rate_from_cache(mock_get_redis: MagicMock) -> None:
    """USD/RUB rate should be returned from Redis cache when available."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = b"89.1234"
    mock_get_redis.return_value = mock_redis

    result = await get_usd_rub_rate()
    assert result == Decimal("89.1234")
    mock_redis.get.assert_called_once()
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.rates.get_redis")
@patch("app.services.rates._fetch_rate_from_cbr")
async def test_get_usd_rub_rate_fetch_and_cache(
    mock_fetch: MagicMock,
    mock_get_redis: MagicMock,
) -> None:
    """USD/RUB rate should be fetched and cached when Redis misses."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_get_redis.return_value = mock_redis

    mock_fetch.return_value = Decimal("90.5678")

    result = await get_usd_rub_rate()
    today = datetime.now(UTC).date().isoformat()
    expected_key = KEY_TMPL.format(date=today)

    assert result == Decimal("90.5678")
    mock_fetch.assert_called_once()
    mock_redis.set.assert_called_once_with(expected_key, "90.5678", ex=600)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_rate_from_cbr_success(mock_http_get: MagicMock) -> None:
    """CBR response should be parsed into Decimal."""

    class MockResponse:
        """Minimal httpx response double for a successful CBR call."""

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, dict[str, dict[str, float]]]:
            return {"Valute": {"USD": {"Value": 92.3456}}}

    mock_http_get.return_value = MockResponse()

    result = await _fetch_rate_from_cbr()
    assert result == Decimal("92.3456")
    mock_http_get.assert_called_once_with(CBR_URL)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_rate_from_cbr_http_error(mock_http_get: MagicMock) -> None:
    """CBR HTTP errors should be propagated after retries fail."""
    from httpx import HTTPStatusError, Request, Response

    mock_response = Response(status_code=500, request=Request("GET", CBR_URL))
    mock_http_get.side_effect = HTTPStatusError(
        "Server Error", request=mock_response.request, response=mock_response
    )

    with pytest.raises(HTTPStatusError):
        await _fetch_rate_from_cbr()
