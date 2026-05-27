"""Unit tests for parcel service behavior."""

from collections.abc import Callable, Sequence
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import BusinessError, NotFoundError, UnauthorizedError
from app.models.parcel import Parcel
from app.schemas.parcel import ParcelCreate, ParcelFilterParams
from app.services.parcel import ParcelService

ParcelCreateFactory = Callable[..., ParcelCreate]
ParcelFactory = Callable[..., Parcel]


def _set_list_result(
    mock_session: AsyncMock,
    total: int,
    parcels: Sequence[Parcel],
) -> MagicMock:
    """Configure mocked SQLAlchemy list query results."""
    mock_session.scalar.return_value = total
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = list(parcels)
    mock_session.scalars.return_value = mock_scalars_result
    return mock_scalars_result


@pytest.mark.asyncio
class TestParcelService:
    """Unit tests for parcel service creation and ownership behavior."""

    async def test_create_valid_parcel(
        self,
        mock_session: AsyncMock,
        parcel_create_factory: ParcelCreateFactory,
    ) -> None:
        """Should create a parcel when input is valid and type exists."""
        # Arrange
        dto = parcel_create_factory()
        session_id = "test-session"
        mock_session.scalar.return_value = dto.parcel_type_id
        svc = ParcelService(mock_session)

        # Act
        parcel = await svc.create_from_dto(dto, session_id)

        # Assert
        assert parcel.name == dto.name
        assert parcel.weight_kg == dto.weight_kg
        assert parcel.session_id == session_id
        assert parcel.declared_value_usd == dto.declared_value_usd
        assert parcel.user_id is None
        mock_session.commit.assert_awaited_once()

    async def test_create_valid_parcel_in_auth_required_mode(
        self,
        mock_session: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
        parcel_create_factory: ParcelCreateFactory,
    ) -> None:
        """Should store ownership in user_id when JWT auth is required."""
        # Arrange
        from app.core.settings import settings

        monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
        dto = parcel_create_factory()
        user_id = str(uuid4())
        mock_session.scalar.return_value = dto.parcel_type_id
        svc = ParcelService(mock_session)

        # Act
        parcel = await svc.create_from_dto(dto, user_id)

        # Assert
        assert parcel.user_id == user_id
        assert parcel.session_id == ""

    async def test_create_invalid_type(
        self,
        mock_session: AsyncMock,
        parcel_create_factory: ParcelCreateFactory,
    ) -> None:
        """Should raise BusinessError if parcel type doesn't exist."""
        # Arrange
        dto = parcel_create_factory()
        mock_session.scalar.return_value = None
        svc = ParcelService(mock_session)

        # Act / Assert
        with pytest.raises(BusinessError, match="Unknown parcel type"):
            await svc.create_from_dto(dto, "session")

    async def test_get_owned_found_and_authorized(
        self,
        mock_session: AsyncMock,
        parcel_factory: ParcelFactory,
    ) -> None:
        """Should return parcel if found and session_id matches."""
        # Arrange
        parcel = parcel_factory(session_id="s1")
        mock_session.scalar.return_value = parcel
        svc = ParcelService(mock_session)

        # Act
        result = await svc.get_owned(parcel.id, "s1")

        # Assert
        assert result == parcel

    async def test_get_owned_found_and_authorized_in_auth_required_mode(
        self,
        mock_session: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
        parcel_factory: ParcelFactory,
    ) -> None:
        """Should authorize by user_id when JWT auth is required."""
        # Arrange
        from app.core.settings import settings

        monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
        user_id = str(uuid4())
        parcel = parcel_factory(session_id="legacy-session", user_id=user_id)
        mock_session.scalar.return_value = parcel
        svc = ParcelService(mock_session)

        # Act
        result = await svc.get_owned(parcel.id, user_id)

        # Assert
        assert result == parcel

    async def test_get_owned_not_found(self, mock_session: AsyncMock) -> None:
        """Should raise NotFoundError if parcel not found."""
        # Arrange
        mock_session.scalar.return_value = None
        svc = ParcelService(mock_session)

        # Act / Assert
        with pytest.raises(NotFoundError, match="Parcel not found"):
            await svc.get_owned("some-id", "s1")

    async def test_get_owned_unauthorized(
        self,
        mock_session: AsyncMock,
        parcel_factory: ParcelFactory,
    ) -> None:
        """Should raise UnauthorizedError if session_id mismatches."""
        # Arrange
        parcel = parcel_factory(id_="123", parcel_type_id=str(uuid4()), session_id="s2")
        mock_session.scalar.return_value = parcel
        svc = ParcelService(mock_session)

        # Act / Assert
        with pytest.raises(UnauthorizedError):
            await svc.get_owned("123", "s1")


@pytest.mark.asyncio
async def test_list_owned_no_filters(
    mock_session: AsyncMock,
    parcel_factory: ParcelFactory,
) -> None:
    """Should return all parcels belonging to a session without filters."""
    # Arrange
    svc = ParcelService(mock_session)
    parcels = [
        parcel_factory(name="Parcel 1", session_id="s1"),
        parcel_factory(name="Parcel 2", session_id="s1"),
        parcel_factory(name="Parcel 3", session_id="s1"),
    ]
    _set_list_result(mock_session, total=3, parcels=parcels)

    # Act
    total, result = await svc.list_owned(
        owner_id="s1",
        filters=ParcelFilterParams(type_id=None, has_cost=None),
        limit=10,
        offset=0,
    )

    # Assert
    assert total == 3
    assert result == parcels
    assert all(p.session_id == "s1" for p in result)


@pytest.mark.asyncio
async def test_list_owned_with_type_and_has_cost_filters(
    mock_session: AsyncMock,
    parcel_factory: ParcelFactory,
) -> None:
    """Should return parcels filtered by type ID and existing delivery cost."""
    # Arrange
    svc = ParcelService(mock_session)
    parcel_type_id = str(uuid4())
    parcels = [
        parcel_factory(
            parcel_type_id=parcel_type_id,
            session_id="s1",
            delivery_cost_rub=Decimal("200.00"),
        )
    ]
    _set_list_result(mock_session, total=1, parcels=parcels)
    filters = ParcelFilterParams(type_id=parcel_type_id, has_cost=True)

    # Act
    total, result = await svc.list_owned(
        owner_id="s1",
        filters=filters,
        limit=10,
        offset=0,
    )

    # Assert
    assert total == 1
    assert result[0].parcel_type_id == parcel_type_id
    assert result[0].delivery_cost_rub is not None


@pytest.mark.asyncio
async def test_list_owned_with_has_cost_false_filter(
    mock_session: AsyncMock,
    parcel_factory: ParcelFactory,
) -> None:
    """Should return parcels without calculated delivery cost."""
    # Arrange
    svc = ParcelService(mock_session)
    parcels = [parcel_factory(session_id="s1", delivery_cost_rub=None)]
    _set_list_result(mock_session, total=1, parcels=parcels)

    # Act
    total, result = await svc.list_owned(
        owner_id="s1",
        filters=ParcelFilterParams(type_id=None, has_cost=False),
        limit=10,
        offset=0,
    )

    # Assert
    assert total == 1
    assert result[0].delivery_cost_rub is None


@pytest.mark.asyncio
async def test_list_owned_with_type_filter_only(
    mock_session: AsyncMock,
    parcel_factory: ParcelFactory,
) -> None:
    """Should return parcels filtered only by type ID."""
    # Arrange
    svc = ParcelService(mock_session)
    parcel_type_id = str(uuid4())
    parcels = [parcel_factory(parcel_type_id=parcel_type_id, session_id="s1")]
    _set_list_result(mock_session, total=1, parcels=parcels)

    # Act
    total, result = await svc.list_owned(
        owner_id="s1",
        filters=ParcelFilterParams(type_id=parcel_type_id, has_cost=None),
        limit=10,
        offset=0,
    )

    # Assert
    assert total == 1
    assert result[0].parcel_type_id == parcel_type_id


@pytest.mark.asyncio
async def test_list_owned_uses_user_ownership_in_auth_required_mode(
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    parcel_factory: ParcelFactory,
) -> None:
    """Should support listing parcels owned by user_id in JWT mode."""
    # Arrange
    from app.core.settings import settings

    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    user_id = str(uuid4())
    svc = ParcelService(mock_session)
    parcels = [parcel_factory(session_id="", user_id=user_id)]
    _set_list_result(mock_session, total=1, parcels=parcels)

    # Act
    total, result = await svc.list_owned(
        owner_id=user_id,
        filters=ParcelFilterParams(type_id=None, has_cost=None),
        limit=10,
        offset=0,
    )

    # Assert
    assert total == 1
    assert result[0].user_id == user_id
    mock_session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_owned_returns_empty_result(mock_session: AsyncMock) -> None:
    """Should return zero total and an empty list when no parcels match."""
    # Arrange
    svc = ParcelService(mock_session)
    _set_list_result(mock_session, total=0, parcels=[])

    # Act
    total, result = await svc.list_owned(
        owner_id="s1",
        filters=ParcelFilterParams(type_id=None, has_cost=None),
        limit=10,
        offset=0,
    )

    # Assert
    assert total == 0
    assert result == []
