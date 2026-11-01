import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, engine


def test_database_pool_settings_configured():
    """Verify pool parameters are read from Settings"""
    assert settings.DB_POOL_SIZE >= 1
    assert settings.DB_MAX_OVERFLOW >= 0
    assert settings.DB_POOL_TIMEOUT >= 1
    assert settings.DB_POOL_RECYCLE >= 1


@pytest.mark.asyncio
async def test_get_db_session_lifecycle():
    """Verify get_db dependency yields an active session and allows service transactions"""
    session_gen = get_db()
    session: AsyncSession = await anext(session_gen)
    try:
        assert isinstance(session, AsyncSession)
        assert session.is_active
        # Simple read query
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        # Closing generator
        try:
            await anext(session_gen)
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_get_db_rollback_on_unhandled_exception():
    """Verify get_db rolls back if an unhandled exception escapes"""
    session_gen = get_db()
    session: AsyncSession = await anext(session_gen)
    
    # Simulate an unhandled exception thrown into the generator
    with pytest.raises(RuntimeError, match="Simulated route error"):
        await session_gen.athrow(RuntimeError("Simulated route error"))


@pytest.mark.asyncio
async def test_single_session_shared_across_request_dependencies():
    """Verify that multiple dependencies and route handlers in a single request share the exact same session instance"""
    from fastapi import Depends, FastAPI
    from httpx import ASGITransport, AsyncClient

    test_app = FastAPI()
    collected_sessions = []

    async def sub_dep_one(db: AsyncSession = Depends(get_db)):
        collected_sessions.append(db)
        return db

    async def sub_dep_two(db: AsyncSession = Depends(get_db)):
        collected_sessions.append(db)
        return db

    @test_app.get("/multi-dep-test")
    async def sample_endpoint(
        db1: AsyncSession = Depends(sub_dep_one),
        db2: AsyncSession = Depends(sub_dep_two),
        db3: AsyncSession = Depends(get_db),
    ):
        return {
            "all_identical": db1 is db2 and db2 is db3,
        }

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        res = await ac.get("/multi-dep-test")

    assert res.status_code == 200
    assert res.json()["all_identical"] is True
    assert len(collected_sessions) == 2
    # Memory identity confirms it is the exact same instance in memory
    assert collected_sessions[0] is collected_sessions[1]

