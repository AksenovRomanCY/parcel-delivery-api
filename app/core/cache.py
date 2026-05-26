"""Redis-based request caching for FastAPI handlers.

Provides decorators and utilities to cache JSON-serializable responses
based on request URL and caller identity. Designed for GET-like idempotent
endpoints whose results can tolerate short TTL-based staleness.

Usage:
@router.get("/resource")
@redis_cache("resource_list", ttl=60)
async def get_resource(request: Request):
    ...
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from app.core.settings import settings
from app.redis_client import get_redis

SESSION_HEADER = "X-Session-Id"
P = ParamSpec("P")
R = TypeVar("R")


def make_cache_key(
    prefix: str,
    request: Request,
    *args: object,
    **kwargs: object,
) -> str:
    """Build an identity-aware cache key from request metadata.

    Uses Authorization header (JWT mode) or X-Session-Id (session mode)
    as the identity component, along with path and query string.
    """
    if settings.AUTH_REQUIRED:
        # Do not store raw bearer tokens in Redis keys. A short hash is enough
        # to separate users while keeping keys non-sensitive.
        auth_header = request.headers.get("Authorization", "anon")
        identity = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
    else:
        identity = request.headers.get(SESSION_HEADER, "anon")

    raw_key = json.dumps(
        {
            "identity": identity,
            "path": str(request.url.path),
            "query": str(request.url.query),
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(raw_key.encode()).hexdigest()
    return f"{prefix}:{digest}"


def make_cache_key_no_session(
    prefix: str,
    request: Request,
    *args: object,
    **kwargs: object,
) -> str:
    """Build a global (non-session-bound) cache key.

    Suitable for caching public GET responses where response does not
    vary between users.

    Args:
        prefix: Namespace prefix to scope cache keys.
        request: FastAPI request object.
        *args: Extra handler arguments accepted for decorator compatibility.
        **kwargs: Extra handler keyword arguments accepted for compatibility.

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
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator for caching FastAPI handler results in Redis.

    Args:
        prefix: Cache namespace prefix (e.g. "parcel_detail").
        ttl: Time-to-live for the cache entry in seconds.
        key_func: Function used to generate cache key from request.

    Returns:
        Callable: A decorator that wraps an async handler function.
    """

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            redis: Redis = get_redis()
            request = cast(Request, args[0] if args else kwargs["request"])

            key = key_func(prefix, request, *args, **kwargs)
            cached = await redis.get(key)
            if cached:
                return cast(R, json.loads(cached))

            result = await fn(*args, **kwargs)

            # FastAPI may return Pydantic models, ORM-backed response models, or
            # plain dicts. jsonable_encoder normalizes all of them before caching.
            serializable = jsonable_encoder(result)
            await redis.set(
                key,
                json.dumps(serializable),
                ex=ttl,
            )
            return result

        return wrapper

    return decorator
