"""Redis-based request caching for FastAPI handlers.

Provides decorators and utilities to cache JSON-serializable responses
based on request URL and session context. Designed for GET-like idempotent
endpoints where response is predictable and not sensitive to timing.

Usage:
@router.get("/resource")
@redis_cache("resource_list", ttl=60)
async def get_resource(request: Request):
    ...
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Coroutine

from fastapi import Request
from redis.asyncio import Redis

from app.redis_client import get_redis

SESSION_HEADER = "X-Session-Id"


def make_cache_key(prefix: str, request: Request, *_, **__) -> str:
    """Build a session-aware cache key from request metadata.

    Includes the session ID, request path, and query string. Used when
    response is user-specific and must be cached per session.

    Args:
        prefix: Namespace prefix to scope cache keys (e.g. "parcel_list").
        request: FastAPI request object used to extract context.

    Returns:
        str: SHA256-based Redis cache key with the given prefix.
    """
    session_id = request.headers.get(SESSION_HEADER, "anon")
    path = str(request.url.path)
    query = str(request.url.query)
    raw_key = json.dumps(
        {
            "session": session_id,
            "path": path,
            "query": query,
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(raw_key.encode()).hexdigest()
    return f"{prefix}:{digest}"


def make_cache_key_no_session(prefix: str, request: Request, *_, **__) -> str:
    """Build a global (non-session-bound) cache key.

    Suitable for caching public GET responses where response does not
    vary between users.

    Args:
        prefix: Namespace prefix to scope cache keys.
        request: FastAPI request object.

    Returns:
        str: SHA256-based Redis key scoped by path and query string.
    """
    raw_key = json.dumps(
        {
            "path": request.url.path,
            "query": request.url.query,
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(raw_key.encode()).hexdigest()
    return f"{prefix}:{digest}"


def redis_cache(
    prefix: str,
    ttl: int = 60,
    key_func: Callable[..., str] = make_cache_key,
):
    """Decorator for caching FastAPI handler results in Redis.

    Args:
        prefix: Cache namespace prefix (e.g. "parcel_detail").
        ttl: Time-to-live for the cache entry in seconds.
        key_func: Function used to generate cache key from request.

    Returns:
        Callable: A decorator that wraps an async handler function.
    """

    def decorator(fn: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(fn)
        async def wrapper(request: Request, *args, **kwargs):
            redis: Redis = get_redis()

            key = key_func(prefix, request, *args, **kwargs)
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)

            result = await fn(request, *args, **kwargs)

            await redis.set(key, json.dumps(result), ex=ttl)
            return result

        return wrapper

    return decorator
