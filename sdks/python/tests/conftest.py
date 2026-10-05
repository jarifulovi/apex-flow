import os
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator
import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Load environment variables from backend .env file before importing app
backend_env = Path(__file__).parent.parent.parent.parent / "apex-flow-backend" / ".env"
if backend_env.exists():
    load_dotenv(backend_env, override=True)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.main import app

# Shared test engine with NullPool
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


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Pytest fixture providing an isolated async database session per test function.
    """
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(autouse=True)
def override_get_db_dependency():
    """
    Autouse fixture overriding FastAPI get_db dependency in app to yield a fresh session per HTTP request.
    """
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        async with TestAsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user_id(db: AsyncSession) -> AsyncGenerator[uuid.UUID, None]:
    """
    Pytest fixture providing a valid user_id present in auth.users table.
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

    try:
        yield user_id
    finally:
        # Guarantee cleanup of test user & related records
        async with TestAsyncSessionLocal() as cleanup_session:
            await cleanup_session.execute(text("DELETE FROM projects WHERE owner_id = :user_id"), {"user_id": user_id})
            await cleanup_session.execute(text("DELETE FROM auth.users WHERE id = :user_id"), {"user_id": user_id})
            await cleanup_session.commit()


@pytest_asyncio.fixture
async def test_project(db: AsyncSession, test_user_id: uuid.UUID) -> AsyncGenerator[Any, None]:
    """
    Creates a test Project owned by test_user_id.
    """
    from app.models.project import Project

    project = Project(owner_id=test_user_id, name="Test Project")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    yield project


@pytest_asyncio.fixture
async def test_project_key(db: AsyncSession, test_project: Any, test_user_id: uuid.UUID) -> AsyncGenerator[str, None]:
    """
    Creates an active ProjectKey record for test_project and yields the raw API key.
    """
    from app.schemas.project_key import ProjectKeyCreate
    from app.services.projects.project_key_service import ProjectKeyService

    created_key = await ProjectKeyService.create_project_key(
        db=db,
        owner_id=test_user_id,
        payload=ProjectKeyCreate(name="Test Key", project_id=test_project.id),
    )
    yield created_key.raw_key
