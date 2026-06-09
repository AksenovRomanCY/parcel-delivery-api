"""Integration test fixtures.

Environment variables are synchronized with the settings singleton before app
runtime modules are used, because ``app.core.settings.Settings()`` may already
have read local ``.env`` values during test collection.
"""

import importlib
import os
import socket
import subprocess
import sys
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.core.settings import Settings


_integration_marker = pytest.mark.integration
_integration_asyncio_marker = pytest.mark.asyncio(loop_scope="session")
ParcelPayloadFactory = Callable[..., dict[str, object]]
AuthContext = tuple[dict[str, str], str]


def _configure_integration_environment() -> None:
    """Force host-run integration tests to use services on localhost."""
    env = {
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3306",
        "DB_USER": "root",
        "DB_PASSWORD": "root",
        "DB_NAME": "delivery_test",
        "REDIS_HOST": "127.0.0.1",
        "REDIS_PORT": "6379",
        "REDIS_PASS": "yourstrongpass",
        "AUTH_REQUIRED": "true",
    }
    os.environ.update(env)

    settings_module = importlib.import_module("app.core.settings")
    settings = cast("Settings", settings_module.__dict__["settings"])

    settings.DB_HOST = env["DB_HOST"]
    settings.DB_PORT = env["DB_PORT"]
    settings.DB_USER = env["DB_USER"]
    settings.DB_PASSWORD = env["DB_PASSWORD"]
    settings.DB_NAME = env["DB_NAME"]
    settings.REDIS_HOST = env["REDIS_HOST"]
    settings.REDIS_PORT = int(env["REDIS_PORT"])
    settings.REDIS_PASS = env["REDIS_PASS"]
    settings.AUTH_REQUIRED = True

    db_session = importlib.import_module("app.db.session")
    if getattr(db_session, "DATABASE_URL", None) != settings.DATABASE_URL:
        importlib.reload(db_session)

    if "app.db.deps" in sys.modules:
        importlib.reload(sys.modules["app.db.deps"])


_configure_integration_environment()


def _strict_integration_mode() -> bool:
    return os.getenv("CI") == "true" or os.getenv("REQUIRE_INTEGRATION_SERVICES") == "1"


def _handle_missing_service(message: str) -> None:
    if _strict_integration_mode():
        pytest.fail(message)
    pytest.skip(message)


def _ensure_integration_services_available() -> None:
    db_host = os.environ["DB_HOST"]
    db_port = int(os.environ["DB_PORT"])
    redis_host = os.environ["REDIS_HOST"]
    redis_port = int(os.environ["REDIS_PORT"])
    redis_password = os.environ.get("REDIS_PASS") or None

    try:
        with socket.create_connection((db_host, db_port), timeout=1):
            pass
    except OSError as exc:
        _handle_missing_service(
            "Integration tests require MySQL at "
            f"{db_host}:{db_port}. Start test services or run only tests/unit/. "
            f"Original error: {exc}"
        )

    redis = Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=True,
    )
    try:
        redis.ping()
    except RedisError as exc:
        _handle_missing_service(
            "Integration tests require Redis at "
            f"{redis_host}:{redis_port}. Start test services or run only tests/unit/. "
            f"Original error: {exc}"
        )
    finally:
        redis.close()


def _ensure_test_database_exists() -> None:
    """Create the configured test database before Alembic targets it."""
    db_name = os.environ["DB_NAME"]
    driver = os.environ.get("DB_PROTOCOL", "mysql+aiomysql").replace(
        "aiomysql", "pymysql"
    )
    server_url = (
        f"{driver}://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@"
        f"{os.environ['DB_HOST']}:{os.environ['DB_PORT']}"
    )
    engine = create_engine(server_url, future=True)
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
    finally:
        engine.dispose()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply integration markers to every test under tests/integration/."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(_integration_marker)
            item.add_marker(_integration_asyncio_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
def _run_migrations() -> None:
    """Run alembic migrations once before all integration tests."""
    _ensure_integration_services_available()
    _ensure_test_database_exists()

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Alembic migration failed:\n{result.stderr}")


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _close_integration_clients() -> AsyncIterator[None]:
    """Close lazy async clients after all integration tests finish."""
    yield

    from app.db.session import engine
    from app.redis_client import close_redis

    await close_redis()
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def _flush_stores() -> None:
    """Flush Redis and clean user/parcel tables before each test."""
    from redis.asyncio import Redis

    from app.core.settings import settings
    from app.db.session import AsyncSessionLocal
    from app.redis_client import get_redis

    redis = get_redis()
    await redis.flushdb()

    # Also flush rate-limit DB (DB 1)
    r1 = Redis.from_url(settings.REDIS_RATE_LIMIT_URL, decode_responses=True)
    await r1.flushdb()
    await r1.aclose()

    # Clean transactional tables for test isolation
    async with AsyncSessionLocal() as session:
        await session.execute(__import__("sqlalchemy").text("DELETE FROM parcel"))
        await session.execute(__import__("sqlalchemy").text("DELETE FROM user"))
        await session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def client() -> AsyncIterator[AsyncClient]:
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
async def auth_context(client: AsyncClient) -> AuthContext:
    """Register a JWT user and return auth headers plus the user ID."""
    from app.core.security import decode_token

    email = f"user-{uuid4()}@example.com"
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    user_id = decode_token(token)
    assert user_id is not None
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture
def parcel_payload_factory() -> ParcelPayloadFactory:
    """Build camelCase parcel API payloads with valid defaults."""

    def _factory(
        parcel_type_id: str,
        name: str = "Test Parcel",
        weight_kg: str = "1.500",
        declared_value_usd: str = "100.00",
        **overrides: object,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": name,
            "weightKg": weight_kg,
            "declaredValueUsd": declared_value_usd,
            "parcelTypeId": parcel_type_id,
        }
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture
def enable_task_admin_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable the manual task endpoint for tests that exercise it."""
    from app.core.settings import settings

    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "test-admin-token")


@pytest.fixture
def admin_headers(enable_task_admin_token: None) -> dict[str, str]:
    """Headers required by operational task endpoints."""
    return {"X-Admin-Token": "test-admin-token"}


@pytest_asyncio.fixture(loop_scope="session")
async def parcel_type_id(client: AsyncClient) -> str:
    """First parcel-type ID from the seeded database."""
    resp = await client.get("/parcel-types")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    return cast(str, items[0]["id"])


@pytest_asyncio.fixture(loop_scope="session")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Direct async DB session for constraint/model-level tests."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
