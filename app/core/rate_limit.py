"""Rate limiting configuration using the limits Redis backend.

The limiter is shared by all routers and attached to ``app.state`` in
``app.main``. Counters use a dedicated Redis DB via ``REDIS_RATE_LIMIT_URL`` so
rate-limit state does not mix with response cache values.
"""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from limits import parse
from limits.aio.storage import RedisStorage
from limits.aio.strategies import FixedWindowRateLimiter
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.settings import settings

P = ParamSpec("P")
R = TypeVar("R")


class RateLimitExceeded(Exception):
    """Raised when a caller exceeds a configured endpoint limit."""

    def __init__(self, detail: str) -> None:
        """Store the human-readable limit detail for response rendering."""
        self.detail = detail
        super().__init__(detail)


class Limiter:
    """Small FastAPI route limiter backed by Redis.

    The public surface intentionally stays tiny: ``@limiter.limit("20/minute")``
    on async route handlers that accept a ``Request`` argument.
    """

    def __init__(self, storage_uri: str) -> None:
        """Create a Redis-backed fixed-window limiter."""
        storage = RedisStorage(storage_uri, implementation="redispy")
        self._strategy = FixedWindowRateLimiter(storage)

    def limit(
        self,
        limit_value: str,
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        """Decorate an async route handler with a fixed-window rate limit."""
        item = parse(limit_value)

        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                request = _find_request(args, kwargs)
                if request is None:
                    msg = "Rate-limited handlers must accept a Request argument"
                    raise RuntimeError(msg)

                if not await self._strategy.hit(
                    item,
                    _route_identifier(request),
                    _remote_address(request),
                ):
                    raise RateLimitExceeded(str(item))

                return await func(*args, **kwargs)

            return wrapper

        return decorator


def _find_request(
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> Request | None:
    """Return the FastAPI request passed to a decorated route handler."""
    request = kwargs.get("request")
    if isinstance(request, Request):
        return request

    for value in args:
        if isinstance(value, Request):
            return value
    return None


def _route_identifier(request: Request) -> str:
    """Build a stable per-route key so endpoint limits stay independent."""
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    return f"{request.method}:{path}"


def _remote_address(request: Request) -> str:
    """Return the client IP used as the rate-limit subject."""
    if request.client is None:
        return "unknown"
    return request.client.host


limiter = Limiter(settings.REDIS_RATE_LIMIT_URL)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Return a stable JSON response for rate-limit failures."""
    return JSONResponse(
        {"error": f"Rate limit exceeded: {exc.detail}"},
        status_code=429,
    )
