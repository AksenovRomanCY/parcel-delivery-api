"""Async client Redis implemented as a lazy Singleton."""

import aioredis

from app.core.settings import settings

__all__ = ["get_redis"]

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Create (on the first call) and return a generic Redis instance."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis
