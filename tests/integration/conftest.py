"""Integration test fixtures.

Environment variables MUST be set before any app module is imported,
because ``app.core.settings.Settings()`` is evaluated at import time.
"""

import os

os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "root")
os.environ.setdefault("DB_NAME", "delivery")
os.environ.setdefault("REDIS_HOST", "127.0.0.1")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_PASS", "")

import subprocess
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

_integration_marker = pytest.mark.integration


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply the ``integration`` marker to every test under tests/integration/."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(_integration_marker)


@pytest.fixture(scope="session", autouse=True)
def _run_migrations():
    """Run alembic migrations once before all integration tests."""
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Alembic migration failed:\n{result.stderr}")


@pytest_asyncio.fixture(autouse=True)
async def _flush_redis():
    """Flush Redis cache (DB 0) and rate-limit store (DB 1) before each test."""
    from app.redis_client import get_redis

    redis = get_redis()
    await redis.flushdb()

    # Also flush rate-limit DB (DB 1)
    from redis.asyncio import Redis

    from app.core.settings import settings

    rl_redis = Redis.from_url(settings.REDIS_RATE_LIMIT_URL, decode_responses=True)
    await rl_redis.flushdb()
    await rl_redis.aclose()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client wired to the FastAPI ASGI app."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def session_id() -> str:
    """Unique session ID for test isolation."""
    return str(uuid4())


@pytest_asyncio.fixture
async def parcel_type_id(client: AsyncClient) -> str:
    """First parcel-type ID from the seeded database."""
    resp = await client.get("/parcel-types")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    return items[0]["id"]


@pytest_asyncio.fixture
async def db_session():
    """Direct async DB session for constraint/model-level tests."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
