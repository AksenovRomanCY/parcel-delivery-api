from .health import router as health_router
from .parcel import router as parcel_router
from .parcel_type import router as parcel_type_router

__all__ = ["health_router", "parcel_type_router", "parcel_router"]
