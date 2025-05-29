"""Schemas for reading parcel type directory entries."""

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel


class ParcelTypeRead(BaseModel):
    """Response schema for parcel type lookup.

    Used in list endpoints or as a nested object in parcel responses.

    Attributes:
        id: Unique identifier (UUIDv4) of the parcel type.
        name: Human-readable category name (e.g., "electronics").
    """

    id: str = Field(..., examples=["b5e96576-3e2b-4bd7-8d6c-7f0cdd3e5a6e"])
    name: str = Field(..., examples=["electronics"])

    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
        "from_attributes": True,
    }
