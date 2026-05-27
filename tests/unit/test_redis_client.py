"""Unit tests for Redis client close functionality."""

from unittest.mock import AsyncMock

import pytest

from app.redis_client import client as redis_module


@pytest.mark.asyncio
async def test_close_redis_resets_singleton() -> None:
    """close_redis should close the connection and reset _redis to None."""
    # Arrange
    mock_redis = AsyncMock()
    redis_module._redis = mock_redis

    # Act
    await redis_module.close_redis()

    # Assert
    mock_redis.aclose.assert_awaited_once()
    assert redis_module._redis is None


@pytest.mark.asyncio
async def test_close_redis_when_none() -> None:
    """close_redis should not raise when _redis is already None."""
    # Arrange
    redis_module._redis = None

    # Act
    await redis_module.close_redis()

    # Assert
    assert redis_module._redis is None
