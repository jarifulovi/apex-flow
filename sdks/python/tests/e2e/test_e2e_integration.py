import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_e2e_full_workflow_and_worker_pipeline(test_project_key: str):
    """
    End-to-End Integration Test:
    Executes a multi-step workflow against real FastAPI backend endpoints and test PostgreSQL DB.
    Verifies step queueing, result reporting, and parent workflow run status updating.
    """
    # 1. Initialize SDK Client configured with test HTTP transport and Project Key
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    # 2. Trigger workflow run execution
    workflow_id = await client.trigger_workflow("order-processing-pipeline")
    assert isinstance(workflow_id, uuid.UUID)

    # 3. Create WorkflowContext
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    # 4. Define step functions
    async def step_1():
        return {"customer_id": "CUST-1001", "item_count": 3}

    async def step_2():
        return {"payment_id": "PAY-888999", "amount": 199.99}

    async def step_3():
        return {"email_status": "sent", "recipient": "user@example.com"}

    async def step_4():
        return {"slack_notification": "delivered"}

    # 5. Execute steps sequentially
    res1 = await ctx.step("extract-info", step_1)
    assert res1["customer_id"] == "CUST-1001"

    res2 = await ctx.step("process-payment", step_2)
    assert res2["payment_id"] == "PAY-888999"

    res3 = await ctx.step("send-email", step_3)
    assert res3["email_status"] == "sent"

    res4 = await ctx.step("notify-slack", step_4)
    assert res4["slack_notification"] == "delivered"

    # Complete workflow explicitly
    await client.complete_workflow(workflow_id)

    # 6. Verify master workflow detail state on control plane backend
    wf_detail_res = await client.http_client.get(f"/api/v1/workflows/{workflow_id}")
    assert wf_detail_res.status_code == 200
    wf_data = wf_detail_res.json()

    assert wf_data["status"] == "completed"
    assert len(wf_data["steps"]) == 4

    step_statuses = {step["step_name"]: step["status"] for step in wf_data["steps"]}
    assert step_statuses["extract-info"] == "success"
    assert step_statuses["process-payment"] == "success"
    assert step_statuses["send-email"] == "success"
    assert step_statuses["notify-slack"] == "success"

    await client.close()


@pytest.mark.asyncio
async def test_cancel_and_restart_workflow_run(test_project_key: str):
    """
    Test Workflow Cancel and Restart API Endpoints:
    Cancelling a workflow run flips status to 'cancelled' and cancels queued steps.
    Restarting a workflow run flips status to 'running' and resets cancelled steps to 'queued'.
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    # 1. Trigger workflow run
    workflow_id = await client.trigger_workflow("cancel-restart-pipeline")

    # 2. Queue step 1 under workflow run
    step_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(workflow_id), "step_name": "step-to-cancel"},
    )
    assert step_res.status_code == 201

    # 3. Cancel workflow run
    cancel_res = await client.http_client.post(f"/api/v1/workflows/{workflow_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "cancelled"
    assert cancel_data["steps"][0]["status"] == "cancelled"

    # 4. Restart workflow run
    restart_res = await client.http_client.post(f"/api/v1/workflows/{workflow_id}/restart")
    assert restart_res.status_code == 200
    restart_data = restart_res.json()
    assert restart_data["status"] == "running"
    assert restart_data["steps"][0]["status"] == "queued"
    assert restart_data["steps"][0]["attempt_count"] == 0

    await client.close()
