import hashlib
import json
from functools import wraps
from typing import Any, Callable, Coroutine

from fastapi import Request
from redis.asyncio import Redis

from app.redis_client import get_redis

SESSION_HEADER = "X-Session-Id"


def make_cache_key(prefix: str, request: Request, *_, **__) -> str:
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
    """Глобальный кэш: учитывает только path и query string."""
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
