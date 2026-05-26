"""Unit tests for Redis cache decorator argument handling."""

from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.core.cache import redis_cache


def _request(path: str = "/items", query_string: bytes = b"") -> Request:
    """Build a minimal Starlette request for cache-key tests."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "query_string": query_string,
            "headers": [],
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


@pytest.mark.asyncio
async def test_redis_cache_passes_keyword_request_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cache key builders should not receive duplicate request kwargs."""
    redis = AsyncMock()
    redis.get.return_value = None
    monkeypatch.setattr("app.core.cache.get_redis", lambda: redis)

    @redis_cache("items")
    async def handler(request: Request, limit: int) -> dict[str, int]:
        return {"limit": limit}

    result = await handler(request=_request(), limit=10)

    assert result == {"limit": 10}
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_redis_cache_passes_positional_request_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cache key builders should not receive duplicate positional request args."""
    redis = AsyncMock()
    redis.get.return_value = None
    monkeypatch.setattr("app.core.cache.get_redis", lambda: redis)

    @redis_cache("items")
    async def handler(request: Request, limit: int) -> dict[str, int]:
        return {"limit": limit}

    result = await handler(_request(), 20)

    assert result == {"limit": 20}
    redis.set.assert_awaited_once()
