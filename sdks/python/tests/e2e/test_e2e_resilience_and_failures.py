import asyncio
import uuid
import pytest
from apex_flow_sdk import ApexFlowClient, WorkflowContext
from tests.helpers.assertions import ApexFlowAssert


@pytest.mark.asyncio
async def test_step_auto_retry_requeue_and_permanent_failure(test_client_harness: ApexFlowClient):
    """
    Test field-level state transitions during step retry exhaustion:
    1. Step reports failure attempt 1 (attempt < max_attempts) -> status resets to 'queued'.
    2. Step reports failure attempt 3 (attempt == max_attempts) -> status transitions to 'failed', parent run transitions to 'failed'.
    """
    client = test_client_harness

    run_id = await client.trigger_workflow("retry-budget-pipeline")
    assert isinstance(run_id, uuid.UUID)

    # Manually create step with max_attempts = 3
    step_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "flaky-external-api", "max_attempts": 3},
    )
    assert step_res.status_code in (200, 201)
    step_id = step_res.json()["id"]

    # 1. Report failure attempt 1 -> re-queued
    rep1 = await client.http_client.post(
        "/api/v1/steps/report",
        json={"step_id": step_id, "status": "failed", "error_message": "503 Service Unavailable", "attempt_count": 1},
    )
    assert rep1.status_code == 200
    step1_data = rep1.json()
    ApexFlowAssert.assert_step(
        step1_data,
        step_name="flaky-external-api",
        status="queued",
        attempt_count=1,
        max_attempts=3,
        error_message="503 Service Unavailable",
    )

    # 2. Report failure attempt 3 -> permanent failure
    rep3 = await client.http_client.post(
        "/api/v1/steps/report",
        json={"step_id": step_id, "status": "failed", "error_message": "Fatal 401 Unauthorized", "attempt_count": 3},
    )
    assert rep3.status_code == 200
    step3_data = rep3.json()
    ApexFlowAssert.assert_step(
        step3_data,
        step_name="flaky-external-api",
        status="failed",
        attempt_count=3,
        max_attempts=3,
        error_message="Fatal 401 Unauthorized",
        completed_at=True,
    )

    # Parent workflow run MUST be marked failed
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    wf_data = wf_res.json()
    ApexFlowAssert.assert_workflow_run(wf_data, status="failed", completed_at=True)


@pytest.mark.asyncio
async def test_workflow_cancel_and_restart_lifecycle(test_client_harness: ApexFlowClient):
    """
    Test workflow run cancellation & restart state machine:
    1. Step 1 succeeds, Step 2 queued.
    2. Run cancelled -> Step 2 becomes 'cancelled', run becomes 'cancelled'.
    3. Run restarted -> Step 2 resets to 'queued' (attempt_count=0), run becomes 'running'.
    4. Execution resumed -> Step 1 skipped (memoized), Step 2 completes, run completes!
    """
    client = test_client_harness

    run_id = await client.trigger_workflow("cancel-restart-suite")
    ctx1 = WorkflowContext(workflow_run_id=run_id, client=client)

    step1_exec_count = 0

    def step1_fn():
        nonlocal step1_exec_count
        step1_exec_count += 1
        return {"auth_token": "TOK-112233"}

    # Execute Step 1
    res1 = await ctx1.step("authenticate-session", step1_fn)
    assert res1["auth_token"] == "TOK-112233"
    assert step1_exec_count == 1

    # Queue Step 2
    await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "fetch-data", "step_order": 2},
    )

    # Cancel workflow run
    cancel_res = await client.http_client.post(f"/api/v1/workflows/{run_id}/cancel")
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()

    ApexFlowAssert.assert_workflow_run(cancel_data, status="cancelled")
    step2_cancelled = [s for s in cancel_data["steps"] if s["step_name"] == "fetch-data"][0]
    ApexFlowAssert.assert_step(step2_cancelled, status="cancelled")

    # Restart workflow run
    restart_res = await client.http_client.post(f"/api/v1/workflows/{run_id}/restart")
    assert restart_res.status_code == 200
    restart_data = restart_res.json()

    ApexFlowAssert.assert_workflow_run(restart_data, status="running")
    step2_restarted = [s for s in restart_data["steps"] if s["step_name"] == "fetch-data"][0]
    ApexFlowAssert.assert_step(step2_restarted, status="queued", attempt_count=0)

    # Resume workflow with brand new context instance
    ctx2 = WorkflowContext(workflow_run_id=run_id, client=client)

    # Step 1 MUST NOT re-execute
    await ctx2.step("authenticate-session", step1_fn)
    assert step1_exec_count == 1

    # Step 2 executes
    res2 = await ctx2.step("fetch-data", lambda: {"records": 150})
    assert res2["records"] == 150

    await client.complete_workflow(run_id)

    # Verify final completed status
    final_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    final_data = final_res.json()
    ApexFlowAssert.assert_workflow_run(final_data, status="completed", completed_at=True)


@pytest.mark.asyncio
async def test_worker_unreachable_backend_resilience():
    """
    Test worker polling loop resilience against an unreachable Control Plane URL.
    """
    unreachable_client = ApexFlowClient(base_url="http://127.0.0.1:59998", project_key="invalid_key")
    worker_task = asyncio.create_task(unreachable_client.start_worker(run_once=False, poll_interval=0.05))

    await asyncio.sleep(0.3)

    worker_task.cancel()
    await unreachable_client.close()


@pytest.mark.asyncio
async def test_targeted_worker_step_names_filtering(test_client_harness: ApexFlowClient):
    """
    Test targeted worker queue filtering by step_names:
    Worker A (polling 'gpu_task') MUST NOT claim 'cpu_task'.
    Worker B (polling 'cpu_task') MUST NOT claim 'gpu_task'.
    """
    client = test_client_harness

    run_id = await client.trigger_workflow("targeted-worker-pipeline")

    # Queue cpu_task and gpu_task
    await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "cpu_task", "step_order": 1},
    )
    await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "gpu_task", "step_order": 2},
    )

    # Worker A polls specifically for gpu_task
    poll_gpu = await client.http_client.post(
        "/api/v1/steps/poll",
        json={"step_names": ["gpu_task"], "worker_name": "gpu-worker", "lock_duration_seconds": 60},
    )
    assert poll_gpu.status_code == 200
    gpu_step = poll_gpu.json()
    assert gpu_step["step_name"] == "gpu_task"

    # Worker B polls specifically for cpu_task
    poll_cpu = await client.http_client.post(
        "/api/v1/steps/poll",
        json={"step_names": ["cpu_task"], "worker_name": "cpu-worker", "lock_duration_seconds": 60},
    )
    assert poll_cpu.status_code == 200
    cpu_step = poll_cpu.json()
    assert cpu_step["step_name"] == "cpu_task"


@pytest.mark.asyncio
async def test_simulated_transient_failure_worker_auto_retry(test_client_harness: ApexFlowClient):
    """
    Test E2E worker execution with SimulatedStepFunction handling transient retries:
    - Step configured to fail the first 2 attempts with a transient error.
    - Worker attempt 1: fails and re-queues step.
    - Worker attempt 2: fails and re-queues step.
    - Worker attempt 3: succeeds! Step state set to success.
    """
    from tests.helpers import simulated_retry_step

    client = test_client_harness
    run_id = await client.trigger_workflow("simulated-retry-pipeline")

    # Queue step with max_attempts=3
    step_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "transient_api_step", "max_attempts": 3},
    )
    assert step_res.status_code in (200, 201)

    # Register simulated step function that fails first 2 attempts
    simulated_fn = simulated_retry_step(fail_attempts=2, error_msg="Simulated 503 Service Unavailable")

    @client.step("transient_api_step")
    async def handle_transient_step(payload):
        return await simulated_fn(payload)

    # Attempt 1: fails & re-queues
    await client.start_worker(step_names=["transient_api_step"], poll_interval=0.01, run_once=True)
    step_res1 = await client.http_client.get(f"/api/v1/steps?limit=10")
    s1 = [s for s in step_res1.json() if s["workflow_run_id"] == str(run_id)][0]
    assert s1["status"] == "queued"
    assert s1["attempt_count"] == 1

    # Attempt 2: fails & re-queues
    await client.start_worker(step_names=["transient_api_step"], poll_interval=0.01, run_once=True)
    step_res2 = await client.http_client.get(f"/api/v1/steps?limit=10")
    s2 = [s for s in step_res2.json() if s["workflow_run_id"] == str(run_id)][0]
    assert s2["status"] == "queued"
    assert s2["attempt_count"] == 2

    # Attempt 3: succeeds!
    await client.start_worker(step_names=["transient_api_step"], poll_interval=0.01, run_once=True)
    step_res3 = await client.http_client.get(f"/api/v1/steps?limit=10")
    s3 = [s for s in step_res3.json() if s["workflow_run_id"] == str(run_id)][0]
    assert s3["status"] == "success"
    assert s3["attempt_count"] == 3

    await client.complete_workflow(run_id)
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    ApexFlowAssert.assert_workflow_run(wf_res.json(), status="completed")


@pytest.mark.asyncio
async def test_simulated_slow_execution_pipeline(test_client_harness: ApexFlowClient):
    """
    Test E2E workflow pipeline with simulated slow step I/O latency.
    """
    from tests.helpers import simulated_slow_step

    client = test_client_harness
    run_id = await client.trigger_workflow("simulated-slow-pipeline")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    slow_step_fn = simulated_slow_step(delay_seconds=0.05, return_val={"computed_matrix": [1, 2, 3]})

    res = await ctx.step("slow_compute_step", slow_step_fn)
    assert res == {"computed_matrix": [1, 2, 3]}

    await client.complete_workflow(run_id)
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    ApexFlowAssert.assert_workflow_run(wf_res.json(), status="completed")

