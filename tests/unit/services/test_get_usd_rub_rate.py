from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.services.rates import (  # noqa
    CBR_URL,
    KEY_TMPL,
    _fetch_rate_from_cbr,
    get_usd_rub_rate,
)


@pytest.mark.asyncio
@patch("app.services.rates.get_redis")
async def test_get_usd_rub_rate_from_cache(mock_get_redis):
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
async def test_get_usd_rub_rate_fetch_and_cache(mock_fetch, mock_get_redis):
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_get_redis.return_value = mock_redis

    mock_fetch.return_value = Decimal("90.5678")

    result = await get_usd_rub_rate()
    today = datetime.now(timezone.utc).date().isoformat()
    expected_key = KEY_TMPL.format(date=today)

    assert result == Decimal("90.5678")
    mock_fetch.assert_called_once()
    mock_redis.set.assert_called_once_with(expected_key, "90.5678", ex=600)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_rate_from_cbr_success(mock_http_get):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"Valute": {"USD": {"Value": 92.3456}}}

    mock_http_get.return_value = MockResponse()

    result = await _fetch_rate_from_cbr()
    assert result == Decimal("92.3456")
    mock_http_get.assert_called_once_with(CBR_URL)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_rate_from_cbr_http_error(mock_http_get):
    from httpx import HTTPStatusError, Request, Response

    mock_response = Response(status_code=500, request=Request("GET", CBR_URL))
    mock_http_get.side_effect = HTTPStatusError(
        "Server Error", request=mock_response.request, response=mock_response
    )

    with pytest.raises(HTTPStatusError):
        await _fetch_rate_from_cbr()
