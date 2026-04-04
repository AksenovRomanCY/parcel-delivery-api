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

import asyncio
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


@pytest.fixture(scope="session")
def event_loop():
    """Share a single event loop across the entire test session.

    This prevents event-loop mismatch errors when module-level singletons
    (SQLAlchemy engine, Redis client) bind to one loop and then subsequent
    tests run on a different loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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

    r1 = Redis.from_url(settings.REDIS_RATE_LIMIT_URL, decode_responses=True)
    await r1.flushdb()
    await r1.aclose()


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
        try:
            yield session
        finally:
            await session.rollback()
