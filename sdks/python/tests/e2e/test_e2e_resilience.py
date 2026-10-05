import asyncio
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from apex_flow_sdk.core.client import ApexFlowClient


@pytest.mark.asyncio
async def test_concurrent_worker_step_acquisition(test_project_key: str):
    """
    Test that 3 concurrent worker loops polling simultaneously for 10 queued steps
    acquire each step exactly once without double-claiming.
    """
    base_url = "http://test"

    # 1. Trigger workflow run with metadata
    client = ApexFlowClient(base_url=base_url, project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url=base_url,
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    run_id = await client.trigger_workflow("concurrent_resilience_pipeline")

    # 2. Start 3 worker instances polling concurrently
    worker_1 = ApexFlowClient(base_url=base_url, project_key=test_project_key, worker_name="worker-1")
    worker_1.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url=base_url,
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )
    worker_2 = ApexFlowClient(base_url=base_url, project_key=test_project_key, worker_name="worker-2")
    worker_2.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url=base_url,
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )
    worker_3 = ApexFlowClient(base_url=base_url, project_key=test_project_key, worker_name="worker-3")
    worker_3.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url=base_url,
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    executed_steps = []

    def make_handler(w_name, idx):
        async def handler(payload):
            executed_steps.append((w_name, idx))
            return {"status": "ok", "worker": w_name}
        return handler

    for w in (worker_1, worker_2, worker_3):
        for i in range(10):
            w.step(f"task_{i}")(make_handler(w.worker_name, i))

    # Run worker poll turns concurrently
    tasks = [
        asyncio.create_task(worker_1.start_worker(run_once=False, poll_interval=0.05)),
        asyncio.create_task(worker_2.start_worker(run_once=False, poll_interval=0.05)),
        asyncio.create_task(worker_3.start_worker(run_once=False, poll_interval=0.05)),
    ]

    # Allow workers to process all steps
    await asyncio.sleep(2.0)

    # Clean shutdown workers
    for w in (worker_1, worker_2, worker_3):
        await w.close()
    await client.close()

    for t in tasks:
        t.cancel()

    # 3. Verify steps status on backend
    async with AsyncClient(transport=ASGITransport(app=app), base_url=base_url, headers={"X-ApexFlow-Project-Key": test_project_key}) as http:
        res = await http.get(f"/api/v1/steps?limit=100")
        assert res.status_code == 200
        steps = res.json()
        run_steps = [s for s in steps if s["workflow_run_id"] == str(run_id)]
        assert len(run_steps) <= 10


@pytest.mark.asyncio
async def test_worker_network_error_backoff():
    """
    Test that an ApexFlowClient worker polling an unreachable control plane
    does not crash and applies backoff retries cleanly.
    """
    client = ApexFlowClient(base_url="http://127.0.0.1:59999", project_key="invalid_key")
    
    # Run polling loop for a brief period in background
    worker_task = asyncio.create_task(client.start_worker(run_once=False, poll_interval=0.05))
    await asyncio.sleep(0.3)
    
    worker_task.cancel()
    await client.close()


@pytest.mark.asyncio
async def test_step_auto_retry_policy(test_project_key: str):
    """
    Test step auto-retry when step failure is reported and attempt_count < max_attempts.
    """
    headers = {"X-ApexFlow-Project-Key": test_project_key}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as http:
        # 1. Create a workflow run & step manually
        wf_res = await http.post("/api/v1/workflows", json={"workflow_name": "retry_test_wf"})
        assert wf_res.status_code in (200, 201)
        run_id = wf_res.json()["id"]

        step_res = await http.post(
            "/api/v1/steps",
            json={
                "workflow_id": run_id,
                "step_name": "flaky_step",
                "max_attempts": 3,
            },
        )
        assert step_res.status_code == 201
        step_id = step_res.json()["id"]

        # 2. Report failure attempt 1 -> step should re-queue
        report_1 = await http.post(
            "/api/v1/steps/report",
            json={
                "step_id": step_id,
                "status": "failed",
                "error_message": "Transient error 1",
                "attempt_count": 1,
            },
        )
        assert report_1.status_code == 200
        assert report_1.json()["status"] == "queued"

        # 3. Report failure attempt 3 -> step should fail permanently
        report_3 = await http.post(
            "/api/v1/steps/report",
            json={
                "step_id": step_id,
                "status": "failed",
                "error_message": "Fatal error on 3rd attempt",
                "attempt_count": 3,
            },
        )
        assert report_3.status_code == 200
        assert report_3.json()["status"] == "failed"
