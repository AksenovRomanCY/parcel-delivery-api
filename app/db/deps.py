from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a SQLAlchemy AsyncSession.

    This function is designed to be used in `Depends(...)` within route
    handlers or services. It ensures proper session lifecycle management
    via `async with`.

    Yields:
        AsyncSession: An active SQLAlchemy async session.
    """
    async with AsyncSessionLocal() as session:
        yield session
