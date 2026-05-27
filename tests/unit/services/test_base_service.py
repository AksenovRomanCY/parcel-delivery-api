"""Unit tests for reusable CRUD service helpers."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.models.parcel_type import ParcelType
from app.services.base import CRUDBase


class ParcelTypeCRUD(CRUDBase[ParcelType]):
    """Concrete CRUD helper used only by tests."""

    model = ParcelType


@pytest.mark.asyncio
async def test_get_delegates_to_session_get(mock_session: AsyncMock) -> None:
    """Get should fetch a model instance by primary key through the session."""
    # Arrange
    row = ParcelType(id="type-id", name="electronics")
    mock_session.get.return_value = row
    service = ParcelTypeCRUD(mock_session)

    # Act
    result = await service.get("type-id")

    # Assert
    assert result == row
    mock_session.get.assert_awaited_once_with(ParcelType, "type-id")


@pytest.mark.asyncio
async def test_list_returns_all_scalar_rows(mock_session: AsyncMock) -> None:
    """List should execute a SELECT and return all scalar rows."""
    # Arrange
    rows = [
        ParcelType(id="type-1", name="clothes"),
        ParcelType(id="type-2", name="electronics"),
    ]
    scalars_result = MagicMock()
    scalars_result.all.return_value = rows
    mock_session.scalars.return_value = scalars_result
    service = ParcelTypeCRUD(mock_session)

    # Act
    result = await service.list()

    # Assert
    assert list(result) == rows
    mock_session.scalars.assert_awaited_once()
    scalars_result.all.assert_called_once_with()


@pytest.mark.asyncio
async def test_commit_adds_commits_and_refreshes_instances(
    mock_session: AsyncMock,
) -> None:
    """_commit should add, commit, and refresh every instance."""
    # Arrange
    first = ParcelType(id="type-1", name="clothes")
    second = ParcelType(id="type-2", name="electronics")
    service = ParcelTypeCRUD(mock_session)

    # Act
    await service._commit(first, second)

    # Assert
    mock_session.add_all.assert_called_once_with((first, second))
    mock_session.commit.assert_awaited_once_with()
    assert mock_session.refresh.await_args_list == [
        call(first),
        call(second),
    ]


@pytest.mark.asyncio
async def test_create_commits_and_returns_instance(mock_session: AsyncMock) -> None:
    """Create should persist and return the same model instance."""
    # Arrange
    row = ParcelType(id="type-id", name="electronics")
    service = ParcelTypeCRUD(mock_session)
    commit = AsyncMock()
    service._commit = commit  # type: ignore[method-assign]

    # Act
    result = await service.create(row)

    # Assert
    assert result == row
    commit.assert_awaited_once_with(row)
