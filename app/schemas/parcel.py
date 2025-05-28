"""Schemes for registering and reading parcels."""

from decimal import Decimal
from typing import Annotated

from pydantic import UUID4, BaseModel, Field, PositiveFloat, condecimal
from pydantic.alias_generators import to_camel

from app.schemas.parcel_type import ParcelTypeRead

# Limitations
NonNegativeMoney = Annotated[
    condecimal(max_digits=14, decimal_places=2, ge=0), "Amount"
]


class ParcelBase(BaseModel):
    name: str = Field(..., max_length=255, examples=["iPhone 15 Pro"])
    weight_kg: PositiveFloat = Field(..., examples=[1.2])
    declared_value_usd: NonNegativeMoney = Field(..., examples=[1299.99])
    parcel_type_id: str = Field(
        ...,
        description="UUID of parcel type",
        examples=["4edc1231-8ec1-4f20-90d1-6f492be3359a"],
    )

    model_config = dict(alias_generator=to_camel, populate_by_name=True)


class ParcelCreate(ParcelBase):
    """Input request schema (POST /parcels)."""

    session_id: str | None = Field(
        None,
        description="Not transmitted by client; filled in by middleware",
        exclude=True,
    )


class ParcelRead(BaseModel):
    """The response pattern when reading/listing parcels."""

    id: str
    name: str
    weight_kg: float
    declared_value_usd: Decimal
    delivery_cost_rub: Decimal | None = Field(
        None, description="If not already calculated — `null`"
    )
    parcel_type: ParcelTypeRead

    model_config = dict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ParcelFilterParams(BaseModel):
    """Query-filters for a parcel list."""

    type_id: UUID4 | None = Field(None, description="Filter by parcel type")
    has_cost: bool | None = Field(
        None,
        description="`true` – only with calculated price, `false` – only without",
    )
