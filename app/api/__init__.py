from .health import router as health_router
from .parcel_types import router as parcel_type_router
from .parcels import router as parcel_router

__all__ = ["health_router", "parcel_type_router", "parcel_router"]
