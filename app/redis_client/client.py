"""Lazy Redis client singleton.

Redis is used by unrelated features (response cache, exchange-rate cache,
rate-limit counters, and scheduler locks), so the connection is opened on first
use and closed explicitly from app/scheduler lifespan hooks.
"""

from redis.asyncio import Redis

from app.core.settings import settings

__all__ = ["get_redis", "close_redis"]

_redis: Redis | None = None


def get_redis() -> Redis:
    """Create on first call and return the app Redis connection."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Close the Redis connection and reset the singleton for graceful shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
