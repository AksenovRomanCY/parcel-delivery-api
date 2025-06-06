"""Main FastAPI application entry point.

Initializes logging, middleware, routers, and OpenAPI configuration
for the Parcel Delivery API.
"""

from fastapi import FastAPI

from app.api import health_router, parcel_router, parcel_type_router
from app.core.logger import setup_logging
from app.core.openapi import setup_custom_openapi
from app.middlewares.session import assign_session_id
from app.tasks.routes import router as task_router

# Initialize structured logging for the application.
setup_logging()

# Create the FastAPI instance with metadata and custom OpenAPI paths.
app = FastAPI(
    title="Parcel-Delivery-API",
    version="0.1.0",
    docs_url="/docs",  # Swagger UI available at /docs
    redoc_url=None,  # Disable ReDoc
    openapi_url="/openapi.json",  # OpenAPI schema endpoint
)

# OpenAPI schema file
setup_custom_openapi(app)

# Register HTTP middleware for assigning session IDs.
app.middleware("http")(assign_session_id)

# Mount modular routers for all API groups.
app.include_router(health_router)
app.include_router(parcel_type_router)
app.include_router(parcel_router)

# Debug-roots to run background tasks manually.
app.include_router(task_router)
