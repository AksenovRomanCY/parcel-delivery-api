"""Rate limiting configuration using slowapi with Redis backend.

The limiter is shared by all routers and attached to ``app.state`` in
``app.main``. Counters use a dedicated Redis DB via ``REDIS_RATE_LIMIT_URL`` so
rate-limit state does not mix with response cache values.
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.settings import settings

limiter = Limiter(
    # The default key is caller IP address. Endpoint decorators can tune limits,
    # while RATE_LIMIT_DEFAULT protects routes that do not specify one.
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.REDIS_RATE_LIMIT_URL,
)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Return a stable JSON response for slowapi rate-limit failures."""
    return JSONResponse(
        {"error": f"Rate limit exceeded: {exc.detail}"},
        status_code=429,
    )
