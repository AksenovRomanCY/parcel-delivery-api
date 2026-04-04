"""Async client Redis implemented as a lazy Singleton."""

from redis.asyncio import Redis

from app.core.settings import settings

__all__ = ["get_redis", "close_redis"]

_redis: Redis | None = None


def get_redis() -> Redis:
    """Create (on the first call) and return a generic Redis instance."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Close the Redis connection and reset the singleton."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
