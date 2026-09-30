import uuid
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Pytest fixture providing an isolated async database session per test function.
    Uses NullPool to prevent asyncpg event loop sharing across pytest async tests.
    """
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )
    TestAsyncSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

    await test_engine.dispose()


@pytest.fixture(autouse=True)
def override_get_db_dependency(db: AsyncSession):
    """
    Autouse fixture that overrides FastAPI get_db dependency in app with the isolated test session.
    """
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user_id(db: AsyncSession) -> AsyncGenerator[uuid.UUID, None]:
    """
    Pytest fixture providing a valid user_id present in auth.users table for testing FKs.
    """
    user_id = uuid.uuid4()
    await db.execute(
        text("""
            INSERT INTO auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at)
            VALUES (:user_id, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', :email, 'dummy_pass', NOW(), '{}', '{}', NOW(), NOW())
        """),
        {"user_id": user_id, "email": f"test-{user_id.hex[:6]}@example.com"},
    )
    await db.commit()

    yield user_id

    # Clean up test user
    await db.execute(text("DELETE FROM auth.users WHERE id = :user_id"), {"user_id": user_id})
    await db.commit()
