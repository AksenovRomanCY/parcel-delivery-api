"""FastAPI dependencies for database session management.

Route handlers depend on these helpers instead of constructing sessions. This
lets tests override ``get_db`` and ensures every request receives a short-lived
``AsyncSession`` bound to the shared engine.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields a SQLAlchemy AsyncSession.

    This function is designed to be used in `Depends(...)` within route
    handlers or services. It ensures proper session lifecycle management
    via `async with`.

    Yields:
        AsyncSession: An active SQLAlchemy async session.
    """
    # The async context manager closes the session after the response is built,
    # even if the route raises an exception handled by FastAPI.
    async with AsyncSessionLocal() as session:
        yield session
