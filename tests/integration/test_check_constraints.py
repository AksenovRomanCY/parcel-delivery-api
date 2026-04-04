"""Integration tests for CHECK constraints at the database level."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.parcel import Parcel


async def test_db_rejects_zero_weight(db_session, parcel_type_id):
    """CHECK constraint should reject weight_kg = 0."""
    parcel = Parcel(
        name="zero-weight",
        weight_kg=Decimal("0"),
        declared_value_usd=Decimal("10.00"),
        session_id=str(uuid4()),
        parcel_type_id=parcel_type_id,
    )
    db_session.add(parcel)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_db_rejects_negative_weight(db_session, parcel_type_id):
    """CHECK constraint should reject weight_kg < 0."""
    parcel = Parcel(
        name="neg-weight",
        weight_kg=Decimal("-1"),
        declared_value_usd=Decimal("10.00"),
        session_id=str(uuid4()),
        parcel_type_id=parcel_type_id,
    )
    db_session.add(parcel)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_db_rejects_negative_declared_value(db_session, parcel_type_id):
    """CHECK constraint should reject declared_value_usd < 0."""
    parcel = Parcel(
        name="neg-value",
        weight_kg=Decimal("1.000"),
        declared_value_usd=Decimal("-5.00"),
        session_id=str(uuid4()),
        parcel_type_id=parcel_type_id,
    )
    db_session.add(parcel)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_db_rejects_negative_delivery_cost(db_session, parcel_type_id):
    """CHECK constraint should reject delivery_cost_rub < 0."""
    parcel = Parcel(
        name="neg-cost",
        weight_kg=Decimal("1.000"),
        declared_value_usd=Decimal("10.00"),
        delivery_cost_rub=Decimal("-1.00"),
        session_id=str(uuid4()),
        parcel_type_id=parcel_type_id,
    )
    db_session.add(parcel)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_db_allows_null_delivery_cost(db_session, parcel_type_id):
    """NULL delivery_cost_rub should be allowed (not yet calculated)."""
    parcel = Parcel(
        name="null-cost",
        weight_kg=Decimal("1.000"),
        declared_value_usd=Decimal("10.00"),
        delivery_cost_rub=None,
        session_id=str(uuid4()),
        parcel_type_id=parcel_type_id,
    )
    db_session.add(parcel)
    await db_session.flush()
    assert parcel.id is not None


async def test_db_allows_valid_values(db_session, parcel_type_id):
    """All-valid data should be accepted."""
    parcel = Parcel(
        name="valid",
        weight_kg=Decimal("2.500"),
        declared_value_usd=Decimal("100.00"),
        delivery_cost_rub=Decimal("50.00"),
        session_id=str(uuid4()),
        parcel_type_id=parcel_type_id,
    )
    db_session.add(parcel)
    await db_session.flush()
    assert parcel.id is not None
