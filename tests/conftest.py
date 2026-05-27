"""Shared pytest fixtures for the test suite."""

import sys
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.parcel import Parcel
from app.schemas.parcel import ParcelCreate

sys.path.append(str(Path(__file__).resolve().parents[1]))


ParcelCreateFactory = Callable[..., ParcelCreate]
ParcelFactory = Callable[..., Parcel]
RequestFactory = Callable[..., Request]


@pytest.fixture
def mock_session() -> AsyncMock:
    """Return an AsyncSession-like mock with common async methods prepared."""
    session = AsyncMock(spec=AsyncSession)
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add_all = MagicMock()
    return session


@pytest.fixture
def parcel_create_factory() -> ParcelCreateFactory:
    """Build ``ParcelCreate`` DTOs with valid defaults."""

    def _factory(
        name: str = "Test Parcel",
        weight_kg: Decimal = Decimal("1.000"),
        declared_value_usd: Decimal = Decimal("100.00"),
        parcel_type_id: str | None = None,
    ) -> ParcelCreate:
        return ParcelCreate(
            name=name,
            weight_kg=weight_kg,
            declared_value_usd=declared_value_usd,
            parcel_type_id=parcel_type_id or str(uuid4()),
        )

    return _factory


@pytest.fixture
def parcel_factory() -> ParcelFactory:
    """Build ``Parcel`` ORM objects with valid defaults."""

    def _factory(
        id_: str | None = None,
        name: str = "Test Parcel",
        weight_kg: Decimal = Decimal("1.000"),
        declared_value_usd: Decimal = Decimal("100.00"),
        parcel_type_id: str | None = None,
        session_id: str = "test-session",
        user_id: str | None = None,
        delivery_cost_rub: Decimal | None = None,
    ) -> Parcel:
        return Parcel(
            id=id_ or str(uuid4()),
            name=name,
            weight_kg=weight_kg,
            declared_value_usd=declared_value_usd,
            parcel_type_id=parcel_type_id or str(uuid4()),
            session_id=session_id,
            user_id=user_id,
            delivery_cost_rub=delivery_cost_rub,
        )

    return _factory


@pytest.fixture
def request_factory() -> RequestFactory:
    """Build minimal Starlette requests for unit tests."""

    def _factory(
        path: str = "/items",
        query_string: bytes = b"",
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> Request:
        return Request(
            {
                "type": "http",
                "method": "GET",
                "path": path,
                "query_string": query_string,
                "headers": headers or [],
                "server": ("testserver", 80),
                "scheme": "http",
            }
        )

    return _factory
