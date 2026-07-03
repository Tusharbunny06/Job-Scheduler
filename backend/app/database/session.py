from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from app.core.config import settings

# Async Engine for FastAPI/Worker
async_engine = create_async_engine(
    settings.async_database_uri,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync Engine for Alembic migrations
sync_engine = create_engine(
    settings.sync_database_uri,
    pool_pre_ping=True
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
