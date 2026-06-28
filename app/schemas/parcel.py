"""Schemas for registering, listing, and filtering parcels.

Field constraints mirror database checks and keep monetary/weight values as
``Decimal`` to avoid float rounding in pricing calculations.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import UUID4, BaseModel, Field
from pydantic.alias_generators import to_camel

from app.schemas.parcel_type import ParcelTypeRead

PositiveWeight = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class ParcelBase(BaseModel):
    """Base fields shared between parcel creation and internal use.

    Camel-case aliases are generated for HTTP clients while Python code can keep
    idiomatic snake_case field access.
    """

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
        "json_schema_extra": {
            "example": {
                "name": "Apple iPhone 15 Pro",
                "weightKg": "1.200",
                "declaredValueUsd": "1299.99",
                "parcelTypeId": "a3a814f4-4724-4947-b6ab-8337f3b33969",
            }
        },
    }


class ParcelCreate(ParcelBase):
    """Request body schema for registering a new parcel."""

    pass


class ParcelCreateResponse(BaseModel):
    """Response returned after parcel registration.

    `owner_id` is the caller identity used by the service: session ID in legacy
    mode and user ID in JWT mode.
    """

    id: str
    owner_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "99e93aee-776d-4bc5-8157-ab80a12b6556",
                "owner_id": "c83e529a-9fa9-4445-a2f5-508e2f10e3de",
            }
        }
    }


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
        "json_schema_extra": {
            "example": {
                "id": "99e93aee-776d-4bc5-8157-ab80a12b6556",
                "name": "Apple iPhone 15 Pro",
                "weightKg": "1.200",
                "declaredValueUsd": "1299.99",
                "deliveryCostRub": None,
                "parcelType": {
                    "id": "a3a814f4-4724-4947-b6ab-8337f3b33969",
                    "name": "electronics",
                },
            }
        },
    }


class ParcelFilterParams(BaseModel):
    """Query parameters used to filter the parcel list.

    ``has_cost`` supports the asynchronous nature of delivery pricing: callers
    can ask for parcels that are still waiting for the background job or those
    already priced.
    """

    type_id: UUID4 | None = Field(None, description="Filter by parcel type")
    has_cost: bool | None = Field(
        None,
        description="`true` – only with calculated price, `false` – only without",
    )
