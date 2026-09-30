import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_full_workflow_and_step_lifecycle_api(
    test_user_id: uuid.UUID, test_project_key: str
):
    """
    Integration test testing full REST API workflow lifecycle:
    Create Workflow -> Queue Step -> Worker Polls Step -> Worker Reports Step Success -> Workflow Completes.
    """
    headers = {"X-ApexFlow-Project-Key": test_project_key}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as ac:

        # 1. Create Workflow
        wf_res = await ac.post(
            "/api/v1/workflows",
            json={"user_id": str(test_user_id), "metadata": {"env": "test"}},
        )
        assert wf_res.status_code == 201
        wf_data = wf_res.json()
        workflow_id = wf_data["id"]
        assert wf_data["status"] == "pending"

        # 2. Queue Step under Workflow
        step_res = await ac.post(
            "/api/v1/steps",
            json={
                "workflow_id": workflow_id,
                "step_name": "extract-data",
                "input_payload": {"query": "parse invoice"},
            },
        )
        assert step_res.status_code == 201
        step_data = step_res.json()
        step_id = step_data["id"]
        assert step_data["status"] == "queued"
        assert step_data["attempt_count"] == 0

        # 3. Worker Polls Queued Step (FOR UPDATE SKIP LOCKED)
        poll_res = await ac.post("/api/v1/steps/poll")
        assert poll_res.status_code == 200
        polled_data = poll_res.json()
        assert polled_data["id"] == step_id
        assert polled_data["status"] == "running"
        assert polled_data["attempt_count"] == 1

        # 4. Worker Reports Step Success
        report_res = await ac.post(
            "/api/v1/steps/report",
            json={
                "step_id": step_id,
                "status": "success",
                "output_payload": {"parsed_total": 120.50},
            },
        )
        assert report_res.status_code == 200
        reported_data = report_res.json()
        assert reported_data["status"] == "success"
        assert reported_data["output_payload"] == {"parsed_total": 120.50}

        # 5. Retrieve Workflow Detail (Verify parent workflow transition to completed)
        detail_res = await ac.get(f"/api/v1/workflows/{workflow_id}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["status"] == "completed"
        assert len(detail_data["steps"]) == 1
        assert detail_data["steps"][0]["id"] == step_id
        assert detail_data["steps"][0]["status"] == "success"
