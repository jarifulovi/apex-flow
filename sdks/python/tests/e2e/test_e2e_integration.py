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
    Comprehensive Test for Workflow Cancel and Restart Engine:
    1. Step 1 executes successfully.
    2. Step 2 is queued. Workflow is cancelled.
    3. Verifies master run is 'cancelled', Step 1 remains 'success', Step 2 is 'cancelled'.
    4. Workflow is restarted.
    5. Verifies master run flips to 'running', Step 2 resets to 'queued' (attempt_count=0).
    6. Resumed WorkflowContext executes: Step 1 function is SKIPPED (memoized checkpoint avoided re-execution), Step 2 executes, and workflow completes!
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    # 1. Trigger workflow run
    run_id = await client.trigger_workflow("cancel-restart-pipeline")
    ctx1 = WorkflowContext(workflow_run_id=run_id, client=client)

    step1_exec_count = 0

    def step1_fn():
        nonlocal step1_exec_count
        step1_exec_count += 1
        return {"data_id": "RAW-99"}

    # Execute Step 1 successfully
    res1 = await ctx1.step("extract-data", step1_fn)
    assert res1["data_id"] == "RAW-99"
    assert step1_exec_count == 1

    # Queue Step 2 under workflow run
    step2_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "process-payment", "step_order": 2},
    )
    assert step2_res.status_code in (200, 201)

    # 2. Cancel workflow run
    cancel_res = await client.http_client.post(f"/api/v1/workflows/{run_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "cancelled"

    # Verify individual step statuses: Step 1 remains 'success', Step 2 is 'cancelled'
    step_statuses = {s["step_name"]: s["status"] for s in cancel_data["steps"]}
    assert step_statuses["extract-data"] == "success"
    assert step_statuses["process-payment"] == "cancelled"

    # 3. Restart workflow run
    restart_res = await client.http_client.post(f"/api/v1/workflows/{run_id}/restart")
    assert restart_res.status_code == 200
    restart_data = restart_res.json()
    assert restart_data["status"] == "running"

    step2_info = [s for s in restart_data["steps"] if s["step_name"] == "process-payment"][0]
    assert step2_info["status"] == "queued"
    assert step2_info["attempt_count"] == 0

    # 4. Resume execution with a brand new WorkflowContext instance on restarted run
    ctx2 = WorkflowContext(workflow_run_id=run_id, client=client)

    # Step 1 MUST NOT re-execute (previously succeeded step is avoided!)
    res1_rebound = await ctx2.step("extract-data", step1_fn)
    assert step1_exec_count == 1  # Execution count is STILL 1!

    # Step 2 executes and succeeds
    res2 = await ctx2.step("process-payment", lambda: {"status": "paid"})
    assert res2["status"] == "paid"

    # Complete workflow explicitly
    await client.complete_workflow(run_id)

    # Verify final status on control plane
    wf_final = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    assert wf_final.status_code == 200
    assert wf_final.json()["status"] == "completed"

    await client.close()
