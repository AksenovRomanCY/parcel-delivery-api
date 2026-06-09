"""FastAPI application composition root.

This is the best starting point for a newcomer reading the runtime wiring:
logging/Sentry, app lifespan, metrics, exception handlers, rate limiting,
authentication mode, OpenAPI schema, and routers are all connected here.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import auth_router, health_router, parcel_router, parcel_type_router
from app.api.errors import register_exception_handlers
from app.core.logger import setup_logging
from app.core.openapi import setup_custom_openapi
from app.core.rate_limit import RateLimitExceeded, limiter, rate_limit_exceeded_handler
from app.core.security import validate_jwt_secret
from app.core.sentry import init_sentry
from app.core.settings import settings
from app.middlewares.session import assign_session_id
from app.redis_client import close_redis
from app.tasks.routes import router as task_router
from app.version import __version__

# Initialize process-wide integrations before the app starts accepting requests.
# Sentry is a no-op unless SENTRY_DSN is configured.
setup_logging()
validate_jwt_secret()
init_sentry(release=__version__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan hook.

    Redis is a lazy singleton shared by cache, rate lookup, and task code. Closing
    it here prevents dangling connections when Uvicorn workers are stopped.
    """
    yield
    await close_redis()


# App metadata and docs endpoints. ReDoc is intentionally disabled so Swagger UI
# remains the single interactive entry point for local exploration.
app = FastAPI(
    title="Parcel-Delivery-API",
    version=__version__,
    docs_url="/docs",  # Swagger UI available at /docs
    redoc_url=None,  # Disable ReDoc
    openapi_url="/openapi.json",  # OpenAPI schema endpoint
    lifespan=lifespan,
)

# HTTP-level Prometheus metrics. The instrumentator reads ENABLE_METRICS, so the
# /metrics endpoint can be disabled per environment without code changes.
Instrumentator(
    should_group_status_codes=True,
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
).instrument(app).expose(app, endpoint="/metrics")

# Convert domain exceptions and validation errors into a consistent JSON shape.
register_exception_handlers(app)

# The rate limiter stores counters in Redis DB 1. Endpoint-specific limits are
# attached on routers with @limiter.limit(...).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Advertise either Bearer JWT auth or legacy X-Session-Id in Swagger.
setup_custom_openapi(app)

# Legacy anonymous mode: callers are identified by X-Session-Id. When
# AUTH_REQUIRED=True, parcel ownership moves to JWT user_id and this middleware
# is not installed.
if not settings.AUTH_REQUIRED:
    logging.getLogger(__name__).warning(
        "legacy_session_auth_enabled: X-Session-Id is deprecated and will be "
        "removed in v2.0.0"
    )
    app.middleware("http")(assign_session_id)

# Mount routers from narrow domains. Keep route-level concerns inside app/api/*
# and business rules inside app/services/*.
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(parcel_type_router)
app.include_router(parcel_router)

# Operational endpoint for manually triggering the delivery-cost recalculation.
app.include_router(task_router)
