import asyncio
import uuid
from datetime import datetime, timezone
import pytest
from apex_flow_sdk import ApexFlowClient, WorkflowContext
from tests.helpers.assertions import ApexFlowAssert


@pytest.mark.asyncio
async def test_concurrent_multi_worker_skip_locked(test_client_harness: ApexFlowClient):
    """
    DBOS Concurrency Equivalence Test:
    Verify that multiple workers polling the queue concurrently using 'FOR UPDATE SKIP LOCKED'
    never double-claim the same step, never deadlock, and process all steps exactly once.
    """
    client = test_client_harness
    run_id = await client.trigger_workflow("multi-worker-competition-pipeline")
    assert isinstance(run_id, uuid.UUID)

    # 1. Queue 6 distinct steps under the workflow
    total_steps = 6
    step_ids = []
    for order in range(1, total_steps + 1):
        res = await client.http_client.post(
            "/api/v1/steps",
            json={
                "workflow_id": str(run_id),
                "step_name": f"step_task_{order}",
                "step_order": order,
                "input_payload": {"item_index": order},
            },
        )
        assert res.status_code in (200, 201)
        step_ids.append(res.json()["id"])

    # 2. Spin up 3 concurrent worker instances competing for the queue
    processed_steps = {}  # step_id -> worker_name
    lock = asyncio.Lock()

    async def worker_loop(worker_name: str):
        while True:
            poll_res = await client.http_client.post(
                "/api/v1/steps/poll",
                json={
                    "worker_name": worker_name,
                    "lock_duration_seconds": 30,
                },
            )
            if poll_res.status_code == 204:
                break
            assert poll_res.status_code == 200
            step_data = poll_res.json()
            curr_id = step_data["id"]

            async with lock:
                # Assert NO double-claiming
                assert curr_id not in processed_steps, f"Step {curr_id} was double-claimed by {worker_name}!"
                processed_steps[curr_id] = worker_name

            # Simulate brief work and report success
            await asyncio.sleep(0.01)
            report_res = await client.http_client.post(
                "/api/v1/steps/report",
                json={
                    "step_id": curr_id,
                    "status": "success",
                    "output_payload": {"processed_by": worker_name},
                },
            )
            assert report_res.status_code == 200

    # Run the 3 workers concurrently
    await asyncio.gather(
        worker_loop("worker_alpha"),
        worker_loop("worker_beta"),
        worker_loop("worker_gamma"),
    )

    # 3. Assertions:
    # All 6 steps were processed
    assert len(processed_steps) == total_steps
    assert set(processed_steps.keys()) == set(step_ids)

    # Complete workflow
    await client.complete_workflow(run_id)

    # Verify workflow is fully completed
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()
    ApexFlowAssert.assert_workflow_run(wf_data, status="completed")
    assert len(wf_data["steps"]) == total_steps
    for step in wf_data["steps"]:
        assert step["status"] == "success"


@pytest.mark.asyncio
async def test_time_travel_workflow_forking(test_client_harness: ApexFlowClient):
    """
    DBOS Rewind Equivalence Test:
    Verify that forking a failed workflow from step N:
    1. Clones prior completed step checkpoints (1..N-1) as memoized without re-executing them.
    2. Resets step N to 'queued' for fresh execution.
    3. Preserves ancestor lineage via forked_from_id while keeping the parent run immutable.
    """
    client = test_client_harness
    parent_run_id = await client.trigger_workflow("parent-pipeline-to-fork")

    ctx_parent = WorkflowContext(workflow_run_id=parent_run_id, client=client)

    step1_call_count = 0
    step2_call_count = 0

    def step_1_fn():
        nonlocal step1_call_count
        step1_call_count += 1
        return {"account_id": "ACC-8877", "tier": "gold"}

    def step_2_fn():
        nonlocal step2_call_count
        step2_call_count += 1
        return {"credit_limit": 50000}

    # Execute Step 1 and Step 2 on parent
    res1 = await ctx_parent.step("fetch_account", step_1_fn)
    assert res1["account_id"] == "ACC-8877"
    assert step1_call_count == 1

    res2 = await ctx_parent.step("verify_credit", step_2_fn)
    assert res2["credit_limit"] == 50000
    assert step2_call_count == 1

    # Step 3 fails on parent
    s3_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(parent_run_id), "step_name": "disburse_funds", "step_order": 3, "max_attempts": 1},
    )
    s3_id = s3_res.json()["id"]
    await client.http_client.post(
        "/api/v1/steps/report",
        json={"step_id": s3_id, "status": "failed", "error_message": "Network Timeout", "attempt_count": 1},
    )

    # Verify parent is failed
    parent_wf = (await client.http_client.get(f"/api/v1/workflows/{parent_run_id}")).json()
    assert parent_wf["status"] == "failed"

    # --- FORK WORKFLOW FROM STEP 3 ---
    forked_run_id = await client.fork_workflow(parent_run_id, from_step_order=3, workflow_name="forked-repaired-run")
    assert isinstance(forked_run_id, uuid.UUID)
    assert forked_run_id != parent_run_id

    # Verify forked run lineage in DB
    forked_wf = (await client.http_client.get(f"/api/v1/workflows/{forked_run_id}")).json()
    assert forked_wf["forked_from_id"] == str(parent_run_id)
    assert forked_wf["status"] == "pending"

    # Reset call counts to prove Steps 1 & 2 are NOT re-executed
    step1_call_count = 0
    step2_call_count = 0
    step3_call_count = 0

    ctx_forked = WorkflowContext(workflow_run_id=forked_run_id, client=client)

    # Resume on forked run: Step 1 MUST use memoized checkpoint from parent
    f_res1 = await ctx_forked.step("fetch_account", step_1_fn)
    assert f_res1["account_id"] == "ACC-8877"
    assert step1_call_count == 0  # NOT CALLED!

    # Step 2 MUST use memoized checkpoint from parent
    f_res2 = await ctx_forked.step("verify_credit", step_2_fn)
    assert f_res2["credit_limit"] == 50000
    assert step2_call_count == 0  # NOT CALLED!

    # Step 3 executes fresh with fixed logic
    def step_3_fixed_fn():
        nonlocal step3_call_count
        step3_call_count += 1
        return {"disbursement_id": "DISB-9999", "status": "settled"}

    f_res3 = await ctx_forked.step("disburse_funds", step_3_fixed_fn)
    assert f_res3["status"] == "settled"
    assert step3_call_count == 1  # CALLED!

    await client.complete_workflow(forked_run_id)

    # Verify forked run is completed
    final_forked = (await client.http_client.get(f"/api/v1/workflows/{forked_run_id}")).json()
    assert final_forked["status"] == "completed"

    # Verify original parent run remains failed (immutable audit history)
    orig_parent = (await client.http_client.get(f"/api/v1/workflows/{parent_run_id}")).json()
    assert orig_parent["status"] == "failed"


@pytest.mark.asyncio
async def test_event_debounce_burst_coalescing(test_client_harness: ApexFlowClient):
    """
    DBOS Debouncer Equivalence Test:
    Verify that rapid bursts of triggers sharing a deduplication_id within a debounce window
    coalesce into a single workflow run, merge metadata, and buffer execution until the quiet window elapses.
    """
    client = test_client_harness
    dedup_key = f"user-action-burst-{uuid.uuid4().hex[:8]}"

    # Fire 5 concurrent triggers in rapid succession
    trigger_tasks = [
        client.trigger_workflow(
            name="debounced-sync-pipeline",
            deduplication_id=dedup_key,
            debounce_seconds=1,
            max_debounce_seconds=3,
            metadata={"burst_index": i, "timestamp": str(datetime.now(timezone.utc))},
        )
        for i in range(5)
    ]
    run_ids = await asyncio.gather(*trigger_tasks)

    # All 5 triggers MUST return the exact same workflow run ID
    first_id = run_ids[0]
    for rid in run_ids:
        assert rid == first_id

    # Verify single workflow run in DB with debounced_until set in the future
    wf_res = await client.http_client.get(f"/api/v1/workflows/{first_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()
    assert wf_data["status"] == "pending"
    assert wf_data["debounced_until"] is not None
    assert wf_data["debounce_seconds"] == 1


@pytest.mark.asyncio
async def test_server_scheduled_retry_delay(test_client_harness: ApexFlowClient):
    """
    DBOS Scheduled Retries Equivalence Test:
    Verify that steps with delay_seconds or retry_delay_seconds are scheduled via available_at,
    hidden from immediate worker polling, and dequeued once available_at matures.
    """
    client = test_client_harness
    run_id = await client.trigger_workflow("scheduled-retry-pipeline")

    # Queue step with 8-second initial delay
    step_res = await client.http_client.post(
        "/api/v1/steps",
        json={
            "workflow_id": str(run_id),
            "step_name": "delayed-dispatch-step",
            "step_order": 1,
            "delay_seconds": 8,
            "max_attempts": 3,
        },
    )
    assert step_res.status_code in (200, 201)
    step_id = step_res.json()["id"]

    # Immediate poll MUST return 204 (hidden because available_at is in the future)
    immediate_poll = await client.http_client.post("/api/v1/steps/poll", json={})
    assert immediate_poll.status_code == 204

    # Wait for the delay to mature
    await asyncio.sleep(8.5)

    # Poll again: step MUST be available now
    matured_poll = await client.http_client.post("/api/v1/steps/poll", json={})
    assert matured_poll.status_code == 200
    polled_step = matured_poll.json()
    assert polled_step["id"] == step_id
    assert polled_step["attempt_count"] == 1

    # Report failure with 8-second server backoff delay
    rep_res = await client.http_client.post(
        "/api/v1/steps/report",
        json={
            "step_id": step_id,
            "status": "failed",
            "error_message": "External API down",
            "attempt_count": 1,
            "retry_delay_seconds": 8,
        },
    )
    assert rep_res.status_code == 200
    assert rep_res.json()["status"] == "queued"

    # Immediate poll during backoff window MUST return 204
    backoff_poll = await client.http_client.post("/api/v1/steps/poll", json={})
    assert backoff_poll.status_code == 204

    # Wait for backoff delay to mature
    await asyncio.sleep(8.5)

    # Poll again: step is available for attempt 2 and succeeds
    attempt2_poll = await client.http_client.post("/api/v1/steps/poll", json={})
    assert attempt2_poll.status_code == 200
    assert attempt2_poll.json()["attempt_count"] == 2

    succ_rep = await client.http_client.post(
        "/api/v1/steps/report",
        json={"step_id": step_id, "status": "success", "output_payload": {"recovered": True}},
    )
    assert succ_rep.status_code == 200
    assert succ_rep.json()["status"] == "success"


@pytest.mark.asyncio
async def test_priority_queue_ordering(test_client_harness: ApexFlowClient):
    """
    DBOS Queue Priority Equivalence Test:
    Verify that queue polling dequeues lower-priority-value (higher urgency) steps first,
    regardless of creation order.
    """
    client = test_client_harness
    run_id = await client.trigger_workflow("priority-queue-pipeline")

    # 1. Queue a low-urgency step first (priority = 10)
    low_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "low_priority_background_task", "step_order": 1, "priority": 10},
    )
    low_id = low_res.json()["id"]

    # 2. Queue a high-urgency step second (priority = 1)
    high_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "high_priority_urgent_task", "step_order": 2, "priority": 1},
    )
    high_id = high_res.json()["id"]

    # 3. Poll queue: The HIGH priority step MUST be dequeued first!
    poll_1 = await client.http_client.post("/api/v1/steps/poll")
    assert poll_1.status_code == 200
    assert poll_1.json()["id"] == high_id
    assert poll_1.json()["step_name"] == "high_priority_urgent_task"

    # 4. Poll queue again: The LOW priority step is dequeued next
    poll_2 = await client.http_client.post("/api/v1/steps/poll")
    assert poll_2.status_code == 200
    assert poll_2.json()["id"] == low_id
    assert poll_2.json()["step_name"] == "low_priority_background_task"


@pytest.mark.asyncio
async def test_loop_safe_step_identity_execution(test_client_harness: ApexFlowClient):
    """
    DBOS Loop Identity Equivalence Test:
    Verify that calling the same step name inside an iterative loop produces distinct, sequenced
    checkpoints (step_order = 1, 2, 3...) that cache and resume independently without collisions.
    """
    client = test_client_harness
    run_id = await client.trigger_workflow("loop-identity-pipeline")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    loop_counts = [0, 0, 0, 0]

    async def dynamic_task(idx: int):
        loop_counts[idx] += 1
        return {"index": idx, "squared": idx * idx}

    # Execute step "compute_square" 4 times in a loop
    results = []
    for i in range(4):
        res = await ctx.step("compute_square", lambda i=i: dynamic_task(i))
        results.append(res)

    assert results == [
        {"index": 0, "squared": 0},
        {"index": 1, "squared": 1},
        {"index": 2, "squared": 4},
        {"index": 3, "squared": 9},
    ]
    assert loop_counts == [1, 1, 1, 1]

    # Verify 4 distinct steps exist in the database with order 1..4
    wf_data = (await client.http_client.get(f"/api/v1/workflows/{run_id}")).json()
    assert len(wf_data["steps"]) == 4
    for idx, s in enumerate(wf_data["steps"]):
        assert s["step_name"] == "compute_square"
        assert s["step_order"] == idx + 1
        assert s["status"] == "success"

    # Resume with a brand new context instance: MUST skip all 4 without re-executing
    ctx_resumed = WorkflowContext(workflow_run_id=run_id, client=client)
    resumed_results = []
    for i in range(4):
        res = await ctx_resumed.step("compute_square", lambda i=i: dynamic_task(i))
        resumed_results.append(res)

    assert resumed_results == results
    # Execution count MUST remain 1 for each iteration (no re-execution!)
    assert loop_counts == [1, 1, 1, 1]
