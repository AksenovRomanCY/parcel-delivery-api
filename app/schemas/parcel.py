"""Schemas for registering, listing, and filtering parcels."""

from decimal import Decimal
from typing import Annotated

from pydantic import UUID4, BaseModel, Field
from pydantic.alias_generators import to_camel

from app.schemas.parcel_type import ParcelTypeRead

PositiveWeight = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class ParcelBase(BaseModel):
    """Base fields shared between parcel creation and internal use."""

    name: str = Field(..., max_length=255, examples=["iPhone 15 Pro"])
    weight_kg: PositiveWeight = Field(..., examples=[1.2])
    declared_value_usd: NonNegativeMoney = Field(..., examples=[1299.99])
    parcel_type_id: str = Field(
        ...,
        description="UUID of parcel type",
        examples=["4edc1231-8ec1-4f20-90d1-6f492be3359a"],
    )

    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
    }


class ParcelCreate(ParcelBase):
    """Request body schema for registering a new parcel."""

    pass


class ParcelRead(BaseModel):
    """Response schema when returning a single parcel or a list item."""

    id: str
    name: str
    weight_kg: Decimal
    declared_value_usd: Decimal
    delivery_cost_rub: Decimal | None = Field(
        None, description="If not already calculated — `null`"
    )
    parcel_type: ParcelTypeRead

    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
        "from_attributes": True,
    }


class ParcelFilterParams(BaseModel):
    """Query parameters used to filter the parcel list."""

    type_id: UUID4 | None = Field(None, description="Filter by parcel type")
    has_cost: bool | None = Field(
        None,
        description="`true` – only with calculated price, `false` – only without",
    )
