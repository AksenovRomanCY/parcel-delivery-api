"""HTTP route modules exposed by the FastAPI application.

Routers are collected here so :mod:`app.main` can mount domain areas without
knowing the file layout inside ``app.api``. Route handlers should stay thin:
translate HTTP concerns, call services, and let shared exception handlers turn
domain errors into response payloads.
"""

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.parcel import router as parcel_router
from app.api.parcel_type import router as parcel_type_router

__all__ = (
    "auth_router",
    "health_router",
    "parcel_router",
    "parcel_type_router",
)
