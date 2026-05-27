"""Unit tests for parcel schemas."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import ParcelCreate, ParcelCreateResponse

ParcelCreateFactory = Callable[..., ParcelCreate]


def test_parcel_create_response_uses_owner_id() -> None:
    """Expose owner_id instead of the legacy session_id field."""
    # Arrange
    response = ParcelCreateResponse(id="parcel-123", owner_id="owner-123")

    # Act
    data = response.model_dump()

    # Assert
    assert data == {
        "id": "parcel-123",
        "owner_id": "owner-123",
    }


def test_parcel_create_accepts_max_length_name(
    parcel_create_factory: ParcelCreateFactory,
) -> None:
    """ParcelCreate should accept a name at the schema maximum length."""
    # Arrange
    name = "x" * 255

    # Act
    dto = parcel_create_factory(name=name)

    # Assert
    assert dto.name == name


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("weight_kg", Decimal("0")),
        ("weight_kg", Decimal("-1.000")),
        ("weight_kg", Decimal("1.0001")),
        ("declared_value_usd", Decimal("-0.01")),
        ("declared_value_usd", Decimal("10.001")),
        ("name", "x" * 256),
    ],
)
def test_parcel_create_rejects_boundary_violations(
    parcel_create_factory: ParcelCreateFactory,
    field: str,
    value: object,
) -> None:
    """ParcelCreate should reject invalid boundary values."""
    # Arrange
    kwargs = {field: value}

    # Act / Assert
    with pytest.raises(ValidationError):
        parcel_create_factory(**kwargs)
