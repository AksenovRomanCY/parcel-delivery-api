from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessError, NotFoundError, UnauthorizedError
from app.models.parcel import Parcel
from app.schemas.parcel import ParcelCreate, ParcelFilterParams
from app.services.parcel import ParcelService


@pytest.mark.asyncio
class TestParcelService:
    async def test_create_valid_parcel(self, mock_session):
        """Should create a parcel when input is valid and type exists."""
        dto = ParcelCreate(
            name="Test Parcel",
            weight_kg=1.0,
            declared_value_usd=Decimal("100.00"),
            parcel_type_id=str(uuid4()),
        )
        session_id = "test-session"

        mock_session.scalar.return_value = dto.parcel_type_id  # simulate type exists
        svc = ParcelService(mock_session)

        parcel = await svc.create_from_dto(dto, session_id)

        assert parcel.name == dto.name
        assert parcel.weight_kg == dto.weight_kg
        assert parcel.session_id == session_id
        assert parcel.declared_value_usd == float(dto.declared_value_usd)

    async def test_create_invalid_type(self, mock_session):
        """Should raise BusinessError if parcel type doesn't exist."""
        dto = ParcelCreate(
            name="Test Parcel",
            weight_kg=1.0,
            declared_value_usd=Decimal("100.00"),
            parcel_type_id=str(uuid4()),
        )
        mock_session.scalar.return_value = None  # simulate missing type
        svc = ParcelService(mock_session)

        with pytest.raises(BusinessError, match="Unknown parcel type"):
            await svc.create_from_dto(dto, "session")

    async def test_get_owned_found_and_authorized(self, mock_session):
        """Should return parcel if found and session_id matches."""
        parcel = Parcel(
            id=str(uuid4()),
            name="X",
            weight_kg=1.0,
            declared_value_usd=100.0,
            parcel_type_id=str(uuid4()),
            session_id="s1",
        )
        mock_session.scalar.return_value = parcel

        svc = ParcelService(mock_session)
        result = await svc.get_owned(parcel.id, "s1")

        assert result == parcel

    async def test_get_owned_not_found(self, mock_session):
        """Should raise NotFoundError if parcel not found."""
        mock_session.scalar.return_value = None
        svc = ParcelService(mock_session)

        with pytest.raises(NotFoundError, match="Parcel not found"):
            await svc.get_owned("some-id", "s1")

    async def test_get_owned_unauthorized(self, mock_session):
        """Should raise UnauthorizedError if session_id mismatches."""
        parcel = Parcel(
            id="123",
            name="X",
            weight_kg=1.0,
            declared_value_usd=100.0,
            parcel_type_id="type",
            session_id="s2",
        )
        mock_session.scalar.return_value = parcel
        svc = ParcelService(mock_session)

        with pytest.raises(UnauthorizedError):
            await svc.get_owned("123", "s1")


@pytest.mark.asyncio
async def test_list_owned_no_filters(mock_session):
    """Should return all parcels belonging to a session without any filters."""
    svc = ParcelService(mock_session)

    # Simulate total count (COUNT(*)) = 3
    mock_session.scalar.return_value = 3  # total count

    # Simulate session.scalars().all() returning 3 parcels
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [
        Parcel(
            id=str(uuid4()),
            name="Parcel 1",
            weight_kg=1,
            declared_value_usd=10,
            parcel_type_id="type1",
            session_id="s1",
        ),
        Parcel(
            id=str(uuid4()),
            name="Parcel 2",
            weight_kg=2,
            declared_value_usd=20,
            parcel_type_id="type2",
            session_id="s1",
        ),
        Parcel(
            id=str(uuid4()),
            name="Parcel 3",
            weight_kg=3,
            declared_value_usd=30,
            parcel_type_id="type3",
            session_id="s1",
        ),
    ]

    mock_session.scalars.return_value = mock_scalars_result

    total, parcels = await svc.list_owned(
        session_id="s1",
        filters=ParcelFilterParams(type_id=None, has_cost=None),
        limit=10,
        offset=0,
    )

    assert total == 3
    assert len(parcels) == 3
    assert all(p.session_id == "s1" for p in parcels)


@pytest.mark.asyncio
async def test_list_owned_with_filters(mock_session):
    """Should return parcels filtered by type ID and having delivery cost."""
    svc = ParcelService(mock_session)

    # Simulate total count = 1 after applying filters
    mock_session.scalar.return_value = 1

    # Simulate scalars().all() returning filtered result
    valid_uuid = str(uuid4())
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [
        Parcel(
            id=str(uuid4()),
            name="Filtered Parcel",
            weight_kg=2,
            declared_value_usd=20,
            parcel_type_id=valid_uuid,
            session_id="s1",
            delivery_cost_rub=200,
        )
    ]

    mock_session.scalars.return_value = mock_scalars_result

    filters = ParcelFilterParams(type_id=valid_uuid, has_cost=True)

    total, parcels = await svc.list_owned(
        session_id="s1",
        filters=filters,
        limit=10,
        offset=0,
    )

    assert total == 1
    assert len(parcels) == 1
    assert parcels[0].parcel_type_id == valid_uuid
    assert parcels[0].delivery_cost_rub is not None
    assert parcels[0].session_id == "s1"
