"""Schemes for a directory of parcel types."""

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel


class ParcelTypeRead(BaseModel):
    id: str = Field(..., examples=["b5e96576-3e2b-4bd7-8d6c-7f0cdd3e5a6e"])
    name: str = Field(..., examples=["electronics"])

    model_config = dict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
