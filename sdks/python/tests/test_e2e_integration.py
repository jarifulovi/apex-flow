import uuid
import pytest
from httpx import ASGITransport, AsyncClient

# Import backend FastAPI app for true end-to-end integration testing
from app.main import app
from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_sdk_and_backend_end_to_end_integration(
    test_user_id: uuid.UUID, test_project_key: str
):
    """
    True End-to-End Integration Test:
    Connects ApexFlow Python SDK directly to FastAPI Backend Control Plane & Live Supabase DB.
    Executes a multi-step workflow with sequential + parallel steps and verifies state checkpointing.
    """
    # Instantiate SDK client hooked directly to ASGI backend transport
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )


    # 1. Trigger workflow on control plane
    workflow_id = await client.trigger_workflow(
        name="e2e-order-process",
        user_id=test_user_id,
        metadata={"environment": "e2e_test"},
    )
    assert workflow_id is not None

    # 2. Instantiate workflow execution context
    ctx = WorkflowContext(workflow_id=workflow_id, client=client)

    # 3. Execute Step 1 (Sequential)
    step1_res = await ctx.step(
        "extract-info",
        lambda: {"amount": 500, "customer": "Alice"},
    )
    assert step1_res == {"amount": 500, "customer": "Alice"}

    # 4. Execute Step 2 (Sequential depending on Step 1)
    step2_res = await ctx.step(
        "process-payment",
        lambda: {"receipt_id": f"REC-{step1_res['amount']}"},
    )
    assert step2_res == {"receipt_id": "REC-500"}

    # 5. Execute Parallel Steps 3 & 4 (Concurrent execution)
    parallel_res = await ctx.parallel([
        ("send-email", lambda: {"email": "sent"}),
        ("notify-slack", lambda: {"slack": "notified"}),
    ])
    assert parallel_res == [{"email": "sent"}, {"slack": "notified"}]

    # 6. Verify master workflow detail state on control plane backend
    wf_detail_res = await client.http_client.get(f"/api/v1/workflows/{workflow_id}")
    assert wf_detail_res.status_code == 200
    wf_data = wf_detail_res.json()

    assert wf_data["status"] == "completed"
    assert len(wf_data["steps"]) == 4

    # Verify all 4 step executions returned success in Supabase
    step_statuses = {step["step_name"]: step["status"] for step in wf_data["steps"]}
    assert step_statuses["extract-info"] == "success"
    assert step_statuses["process-payment"] == "success"
    assert step_statuses["send-email"] == "success"
    assert step_statuses["notify-slack"] == "success"

    await client.close()
