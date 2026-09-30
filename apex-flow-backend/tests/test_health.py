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
