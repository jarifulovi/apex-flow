import asyncio
import uuid
import pytest
from apex_flow_sdk import ApexFlowClient, WorkflowContext
from tests.helpers.assertions import ApexFlowAssert


@pytest.mark.asyncio
async def test_multi_step_pipeline_execution_and_data_flow(test_client_harness: ApexFlowClient):
    """
    Rigorously test sequential multi-step workflow pipeline execution, data passing,
    and field-level state consistency across all step transitions.
    """
    client = test_client_harness

    # 1. Trigger workflow run
    run_id = await client.trigger_workflow("order-processing-pipeline", metadata={"source": "pytest"})
    assert isinstance(run_id, uuid.UUID)

    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    # 2. Define step logic
    async def step_1():
        return {"customer_id": "CUST-9900", "items": ["laptop", "mouse"]}

    async def step_2():
        return {"payment_id": "PAY-12345", "amount": 1250.00, "status": "authorized"}

    async def step_3():
        return {"shipment_tracking": "TRK-987654321", "carrier": "FedEx"}

    # 3. Execute step 1
    res1 = await ctx.step("validate-customer", step_1)
    assert res1["customer_id"] == "CUST-9900"

    # Verify backend step 1 state
    s1_res = await client.http_client.get(f"/api/v1/steps?limit=10")
    assert s1_res.status_code == 200
    steps = [s for s in s1_res.json() if s["workflow_run_id"] == str(run_id)]
    step1_data = [s for s in steps if s["step_name"] == "validate-customer"][0]

    ApexFlowAssert.assert_step(
        step1_data,
        step_name="validate-customer",
        status="success",
        attempt_count=1,
        max_attempts=3,
        output_payload={"customer_id": "CUST-9900", "items": ["laptop", "mouse"]},
        completed_at=True,
    )

    # 4. Execute step 2 & 3
    res2 = await ctx.step("process-payment", step_2)
    assert res2["payment_id"] == "PAY-12345"

    res3 = await ctx.step("create-shipment", step_3)
    assert res3["carrier"] == "FedEx"

    # Complete workflow explicitly
    await client.complete_workflow(run_id)

    # 5. Fetch workflow detail and validate all field states strictly
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()

    ApexFlowAssert.assert_workflow_run(
        wf_data,
        workflow_name="order-processing-pipeline",
        status="completed",
        started_at=True,
        completed_at=True,
    )

    assert len(wf_data["steps"]) == 3
    for s in wf_data["steps"]:
        ApexFlowAssert.assert_step(s, status="success", attempt_count=1)


@pytest.mark.asyncio
async def test_step_memoization_checkpoint_resumption(test_client_harness: ApexFlowClient):
    """
    Test durable step memoization & resumption:
    1. Step 1 executes successfully.
    2. Context is destroyed/re-created.
    3. Re-executing step 1 uses memoized result without calling step function body again.
    """
    client = test_client_harness

    run_id = await client.trigger_workflow("memoization-pipeline")
    ctx1 = WorkflowContext(workflow_run_id=run_id, client=client)

    step1_exec_count = 0

    def step1_fn():
        nonlocal step1_exec_count
        step1_exec_count += 1
        return {"checkpoint": "V1", "value": 42}

    # First execution
    res1 = await ctx1.step("checkpoint-step", step1_fn)
    assert res1["value"] == 42
    assert step1_exec_count == 1

    # Destroy & create new context for same run
    ctx2 = WorkflowContext(workflow_run_id=run_id, client=client)

    # Second execution MUST skip function call and return memoized result
    res1_rebound = await ctx2.step("checkpoint-step", step1_fn)
    assert res1_rebound["value"] == 42
    assert step1_exec_count == 1  # Execution count MUST remain 1!

    # Execute new step 2 on resumed context
    res2 = await ctx2.step("next-step", lambda: {"status": "done"})
    assert res2["status"] == "done"

    await client.complete_workflow(run_id)

    # Field-level verification
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    wf_data = wf_res.json()
    ApexFlowAssert.assert_workflow_run(wf_data, status="completed")
    assert len(wf_data["steps"]) == 2


@pytest.mark.asyncio
async def test_child_workflow_lineage_tracking(test_client_harness: ApexFlowClient):
    """
    Test parent-child workflow triggering and lineage tracking.
    """
    client = test_client_harness

    parent_id = await client.trigger_workflow("parent-workflow", metadata={"role": "parent"})
    assert isinstance(parent_id, uuid.UUID)

    child_id = await client.trigger_workflow(
        "child-workflow",
        metadata={"role": "child"},
        parent_workflow_id=parent_id,
    )
    assert isinstance(child_id, uuid.UUID)

    # Complete parent and child workflows
    await client.complete_workflow(child_id)
    await client.complete_workflow(parent_id)

    # Validate parent and child workflow runs
    child_res = await client.http_client.get(f"/api/v1/workflows/{child_id}")
    child_data = child_res.json()
    ApexFlowAssert.assert_workflow_run(
        child_data,
        workflow_name="child-workflow",
        status="completed",
        parent_workflow_id=str(parent_id),
    )

    parent_res = await client.http_client.get(f"/api/v1/workflows/{parent_id}")
    parent_data = parent_res.json()
    ApexFlowAssert.assert_workflow_run(
        parent_data,
        workflow_name="parent-workflow",
        status="completed",
    )


@pytest.mark.asyncio
async def test_workflow_deduplication_idempotency(test_client_harness: ApexFlowClient):
    """
    Test workflow trigger idempotency via deduplication_id.
    """
    client = test_client_harness
    dedup_key = f"dedup-{uuid.uuid4().hex[:8]}"

    # Trigger first workflow with deduplication_id
    run_id_1 = await client.trigger_workflow("idempotent-pipeline", deduplication_id=dedup_key)

    # Trigger second workflow with duplicate deduplication_id
    run_id_2 = await client.trigger_workflow("idempotent-pipeline", deduplication_id=dedup_key)

    # Both IDs MUST match exactly
    assert run_id_1 == run_id_2

    # Verify single workflow run exists
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id_1}")
    wf_data = wf_res.json()
    ApexFlowAssert.assert_workflow_run(wf_data, deduplication_id=dedup_key, status="pending")


@pytest.mark.asyncio
async def test_parallel_steps_execution_with_gather(test_client_harness: ApexFlowClient):
    """
    Test concurrent step execution within a single workflow using asyncio.gather.
    """
    client = test_client_harness

    run_id = await client.trigger_workflow("parallel-branches-pipeline")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    async def fetch_branch_a():
        await asyncio.sleep(0.01)
        return {"source": "branch_a", "metrics": [1, 2, 3]}

    async def fetch_branch_b():
        await asyncio.sleep(0.01)
        return {"source": "branch_b", "metrics": [4, 5, 6]}

    # Execute both steps concurrently
    res_a, res_b = await asyncio.gather(
        ctx.step("branch-a-step", fetch_branch_a),
        ctx.step("branch-b-step", fetch_branch_b),
    )

    assert res_a["source"] == "branch_a"
    assert res_b["source"] == "branch_b"

    await client.complete_workflow(run_id)

    # Verify both steps recorded in database in success status
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()

    ApexFlowAssert.assert_workflow_run(wf_data, status="completed")
    assert len(wf_data["steps"]) == 2
    for step in wf_data["steps"]:
        ApexFlowAssert.assert_step(step, status="success")

