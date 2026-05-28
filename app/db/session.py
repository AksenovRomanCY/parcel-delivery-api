"""Async SQLAlchemy engine and session factory configuration.

This module is the single place where the application creates the database
engine. FastAPI requests receive sessions from ``app.db.deps.get_db`` and
background jobs create sessions from ``AsyncSessionLocal`` directly.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.settings import settings

# Fully qualified database URL from environment or .env file. Reading it once
# here makes imports deterministic for request handlers and scheduler workers.
DATABASE_URL = settings.DATABASE_URL

# Async-compatible SQLAlchemy engine. The configured default targets MySQL via
# aiomysql, but the URL is assembled from settings for deployment flexibility.
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Enable SQL logging; disable in production if noisy
    future=True,
)

# Session factory for async context managers. expire_on_commit=False keeps ORM
# attributes readable after service methods commit and return objects to routers.
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,  # Keep attributes accessible after commit
)
