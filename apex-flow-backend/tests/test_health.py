import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_liveness_endpoint():
    """Verify lightweight /health endpoint returns status ok without DB connection"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_readiness_endpoint():
    """Verify /health/db endpoint checks database ping"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/health/db")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["project"] == "ApexFlow Control Plane"
    assert "database" in data


@pytest.mark.asyncio
async def test_health_readiness_failure_returns_503():
    """Verify /health/db returns 503 when database ping fails"""
    from unittest.mock import AsyncMock
    from app.core.database import get_db

    mock_session = AsyncMock()
    mock_session.execute.side_effect = ConnectionRefusedError("Database connection lost")

    async def mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/health/db")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert "unhealthy: Database connection lost" in data["database"]
    finally:
        del app.dependency_overrides[get_db]
