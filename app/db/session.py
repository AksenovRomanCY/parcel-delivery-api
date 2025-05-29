"""Async SQLAlchemy engine and session factory configuration.

This module sets up the async engine and sessionmaker for use
throughout the application.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.settings import settings

# Fully qualified database URL from environment or .env file
DATABASE_URL = settings.DATABASE_URL

# Async-compatible SQLAlchemy engine (e.g., for MySQL, PostgreSQL)
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Enable SQL logging; disable in production if noisy
    future=True,
)

# Session factory for async context, used with `async with`
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,  # Keep attributes accessible after commit
)
