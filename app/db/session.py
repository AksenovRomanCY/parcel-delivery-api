from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.settings import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
