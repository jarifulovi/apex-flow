import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_central_exception_handler_not_found():
    """Verify EntityNotFoundException returns standardized JSON response structure with HTTP 404"""
    dummy_id = uuid.uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get(f"/api/v1/workflows/{dummy_id}")

    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "ENTITY_NOT_FOUND"
    assert f"Workflow with ID '{dummy_id}' not found." in data["error"]["message"]
    assert data["error"]["details"]["entity_name"] == "Workflow"
