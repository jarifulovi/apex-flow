import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_e2e_large_payload_offloading_and_dereferencing(test_project_key: str):
    """Verify >250KB payload offloading, DB descriptor ref creation, and SDK auto-dereferencing."""
    transport = ASGITransport(app=app)
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key, worker_name="e2e-payload-worker")
    client.http_client = AsyncClient(transport=transport, base_url="http://test", headers={"X-ApexFlow-Project-Key": test_project_key})

    # 1. Trigger workflow
    run_id = await client.trigger_workflow(
        name="test_large_payload_wf",
        metadata={"e2e_test": True},
    )
    assert isinstance(run_id, uuid.UUID)

    # 2. Register workflow with large payload step
    received_dataset = {}

    @client.workflow("test_large_payload_wf")
    async def test_wf(ctx: WorkflowContext, input_data: dict):
        nonlocal received_dataset

        async def generate_large_payload():
            # Build 300KB dictionary
            big_str = "ApexFlow Large Payload E2E Test Token " * 100
            return {"items": [{"id": i, "content": big_str} for i in range(80)]}

        dataset = await ctx.step("step_large_output", generate_large_payload)

        async def consume_large_payload():
            return {"item_count": len(dataset.get("items", []))}

        res = await ctx.step("step_consume_input", consume_large_payload)
        received_dataset = dataset
        return res

    # Queue step 1 to kick off execution
    async with AsyncClient(transport=transport, base_url="http://test", headers={"X-ApexFlow-Project-Key": test_project_key}) as http:
        q_res = await http.post(
            "/api/v1/steps",
            json={
                "workflow_id": str(run_id),
                "step_name": "step_large_output",
                "step_order": 1,
                "input_payload": {"initial": True},
            },
        )
        assert q_res.status_code in (200, 201)

    # 3. Start worker to execute workflow
    await client.start_worker(step_names=["step_large_output"], poll_interval=0.01, run_once=True)

    # 4. Verify received dataset in Python SDK was dereferenced back to 80 items
    assert "items" in received_dataset
    assert len(received_dataset["items"]) == 80

    # 5. Verify Control Plane DB state has $apexflow_ref descriptor for step_large_output
    async with AsyncClient(transport=transport, base_url="http://test", headers={"X-ApexFlow-Project-Key": test_project_key}) as http:
        run_res = await http.get(f"/api/v1/workflows/{run_id}")
        assert run_res.status_code == 200
        run_detail = run_res.json()
        assert run_detail["status"] == "completed"

        steps = {s["step_name"]: s for s in run_detail["steps"]}
        assert "step_large_output" in steps

        step_output = steps["step_large_output"]["output_payload"]
        assert isinstance(step_output, dict)
        assert step_output.get("$apexflow_ref") is True
        assert "key" in step_output
        assert step_output.get("size_bytes", 0) > 250000

        # 6. Test direct GET download endpoint
        storage_key = step_output["key"]
        dl_res = await http.get(f"/api/v1/storage/download/{storage_key}")
        assert dl_res.status_code == 200
        dl_json = dl_res.json()
        assert "items" in dl_json
        assert len(dl_json["items"]) == 80

    await client.close()
