from .auth import router as auth_router
from .health import router as health_router
from .parcel import router as parcel_router
from .parcel_type import router as parcel_type_router

__all__ = ["auth_router", "health_router", "parcel_type_router", "parcel_router"]
