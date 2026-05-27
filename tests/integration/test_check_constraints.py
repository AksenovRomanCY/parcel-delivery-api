"""Integration tests for CHECK constraints at the database level."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parcel import Parcel

# MySQL may raise either IntegrityError or OperationalError (wrapped as
# DatabaseError) for CHECK constraint violations depending on the driver.
_check_error = (IntegrityError, DatabaseError)
ParcelFactory = Callable[..., Parcel]


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "zero-weight", "weight_kg": Decimal("0")},
        {"name": "neg-weight", "weight_kg": Decimal("-1")},
        {"name": "neg-value", "declared_value_usd": Decimal("-5.00")},
        {"name": "neg-cost", "delivery_cost_rub": Decimal("-1.00")},
    ],
)
async def test_db_rejects_check_constraint_violations(
    db_session: AsyncSession,
    parcel_type_id: str,
    parcel_factory: ParcelFactory,
    overrides: dict[str, object],
) -> None:
    """CHECK constraints should reject invalid parcel numeric values."""
    # Arrange
    parcel = parcel_factory(parcel_type_id=parcel_type_id, **overrides)
    db_session.add(parcel)

    # Act / Assert
    with pytest.raises(_check_error):
        await db_session.flush()


@pytest.mark.parametrize("delivery_cost_rub", [None, Decimal("50.00")])
async def test_db_allows_valid_values(
    db_session: AsyncSession,
    parcel_type_id: str,
    parcel_factory: ParcelFactory,
    delivery_cost_rub: Decimal | None,
) -> None:
    """Valid parcel data should be accepted by database constraints."""
    # Arrange
    parcel = parcel_factory(
        name="valid",
        weight_kg=Decimal("2.500"),
        declared_value_usd=Decimal("100.00"),
        delivery_cost_rub=delivery_cost_rub,
        parcel_type_id=parcel_type_id,
    )
    db_session.add(parcel)

    # Act
    await db_session.flush()

    # Assert
    assert parcel.id is not None
