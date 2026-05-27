"""Unit tests for Redis cache decorator argument handling."""

from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.core.cache import redis_cache

RequestFactory = Callable[..., Request]


@pytest.mark.parametrize(
    ("call_style", "limit"),
    [
        ("keyword", 10),
        ("positional", 20),
    ],
)
@pytest.mark.asyncio
async def test_redis_cache_passes_request_once(
    monkeypatch: pytest.MonkeyPatch,
    request_factory: RequestFactory,
    call_style: str,
    limit: int,
) -> None:
    """Cache key builders should not receive duplicate request args."""
    # Arrange
    redis = AsyncMock()
    redis.get.return_value = None
    monkeypatch.setattr("app.core.cache.get_redis", lambda: redis)

    @redis_cache("items")
    async def handler(request: Request, limit: int) -> dict[str, int]:
        return {"limit": limit}

    # Act
    if call_style == "keyword":
        result = await handler(request=request_factory(), limit=limit)
    else:
        result = await handler(request_factory(), limit)

    # Assert
    assert result == {"limit": limit}
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_redis_cache_returns_cached_value_without_calling_handler(
    monkeypatch: pytest.MonkeyPatch,
    request_factory: RequestFactory,
) -> None:
    """Cache hits should return Redis data and skip the wrapped handler."""
    # Arrange
    redis = AsyncMock()
    redis.get.return_value = '{"limit": 30}'
    monkeypatch.setattr("app.core.cache.get_redis", lambda: redis)
    handler_calls = 0

    @redis_cache("items")
    async def handler(request: Request, limit: int) -> dict[str, int]:
        nonlocal handler_calls
        handler_calls += 1
        return {"limit": limit}

    # Act
    result = await handler(request_factory(), 30)

    # Assert
    assert result == {"limit": 30}
    assert handler_calls == 0
    redis.set.assert_not_awaited()
