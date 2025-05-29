import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add_all = MagicMock()
    return session
