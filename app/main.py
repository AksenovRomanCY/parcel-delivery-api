"""Main FastAPI application entry point.

Initializes logging, middleware, routers, and OpenAPI configuration
for the Parcel Delivery API.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth_router, health_router, parcel_router, parcel_type_router
from app.api.errors import register_exception_handlers
from app.core.logger import setup_logging
from app.core.openapi import setup_custom_openapi
from app.core.rate_limit import limiter
from app.core.sentry import init_sentry
from app.core.settings import settings
from app.middlewares.session import assign_session_id
from app.redis_client import close_redis
from app.tasks.routes import router as task_router

# Initialize structured logging and Sentry error tracking.
setup_logging()
init_sentry(release="0.1.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: clean up Redis on shutdown."""
    yield
    await close_redis()


# Create the FastAPI instance with metadata and custom OpenAPI paths.
app = FastAPI(
    title="Parcel-Delivery-API",
    version="0.1.0",
    docs_url="/docs",  # Swagger UI available at /docs
    redoc_url=None,  # Disable ReDoc
    openapi_url="/openapi.json",  # OpenAPI schema endpoint
    lifespan=lifespan,
)

# Prometheus metrics instrumentation.
Instrumentator(
    should_group_status_codes=True,
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
).instrument(app).expose(app, endpoint="/metrics")

# Register custom exception handlers for structured error responses.
register_exception_handlers(app)

# Rate limiting via slowapi.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# OpenAPI schema file
setup_custom_openapi(app)

# Register HTTP middleware for assigning session IDs (legacy mode).
if not settings.AUTH_REQUIRED:
    app.middleware("http")(assign_session_id)

# Mount modular routers for all API groups.
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(parcel_type_router)
app.include_router(parcel_router)

# Debug-roots to run background tasks manually.
app.include_router(task_router)
