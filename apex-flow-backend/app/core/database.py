from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create asynchronous database engine
engine_kwargs = {
    "echo": settings.DB_ECHO,
    "future": True,
    "pool_pre_ping": True,
}

# Apply connection pool settings for PostgreSQL
if "postgresql" in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "connect_args": {"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Asynchronous session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Declarative base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass


# Dependency for injection into FastAPI endpoint handlers
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency yielding an AsyncSession.
    Services are responsible for committing transactions (or using `async with session.begin():`).
    Rolls back automatically only if an unhandled exception escapes the endpoint handler.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
