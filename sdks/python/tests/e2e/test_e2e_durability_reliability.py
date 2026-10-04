import asyncio
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from app.main import app
from app.models import WorkflowStep
from conftest import TestAsyncSessionLocal
from apex_flow_sdk import (
    ApexFlowClient,
    WorkflowContext,
    validate_response,
    NonRetryableError,
    StepFailedError,
)


@pytest.mark.asyncio
async def test_durable_checkpoint_resumption(test_project_key: str):
    """
    Test Durable Checkpointing & Resumption:
    Step 1 completes. Execution crashes/restarts.
    New WorkflowContext instance resumes execution: Step 1 function is SKIPPED (loaded from DB), Step 2 executes.
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    # 1. Trigger workflow run
    run_id = await client.trigger_workflow("durable-lead-pipeline")
    ctx1 = WorkflowContext(workflow_run_id=run_id, client=client)

    step1_execution_counter = 0

    def step1_fn():
        nonlocal step1_execution_counter
        step1_execution_counter += 1
        return {"lead_id": "LEAD-101", "name": "Alice"}

    # Execute Step 1
    res1 = await ctx1.step("extract-lead", step1_fn)
    assert res1["lead_id"] == "LEAD-101"
    assert step1_execution_counter == 1

    # SIMULATE WORKER CRASH / RESTART: Create a brand new WorkflowContext
    ctx2 = WorkflowContext(workflow_run_id=run_id, client=client)

    # Re-run Step 1 and execute Step 2 on the new context
    res1_rebound = await ctx2.step("extract-lead", step1_fn)
    assert step1_execution_counter == 1  # Step 1 was NOT re-executed! Loaded from checkpoint!

    res2 = await ctx2.step("enrich-lead", lambda: {"status": "enriched", "score": 95})
    assert res2["score"] == 95

    # Complete workflow explicitly
    await client.complete_workflow(run_id)

    # Verify run completed on control plane
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    assert wf_res.status_code == 200
    assert wf_res.json()["status"] == "completed"

    await client.close()


@pytest.mark.asyncio
async def test_step_retry_resilience(test_project_key: str):
    """
    Test Resilient Retries:
    Step function fails twice before succeeding on attempt 3.
    Verifies step succeeds and parent workflow completes.
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    run_id = await client.trigger_workflow("flaky-step-workflow")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    attempt_counter = 0

    def flaky_fn():
        nonlocal attempt_counter
        attempt_counter += 1
        if attempt_counter < 3:
            raise ValueError(f"Temporary network error on attempt {attempt_counter}")
        return {"result": "success_after_retries"}

    # Execute step with 3 retries
    res = await ctx.step("flaky-step", flaky_fn, retries=3, backoff_factor=0.01)
    assert res["result"] == "success_after_retries"
    assert attempt_counter == 3

    await client.close()


@pytest.mark.asyncio
async def test_silent_error_detection_and_retry(test_project_key: str):
    """
    Test Silent API Error Detection & Retry:
    API returns silent JSON error `{"success": False}` on attempt 1 & 2.
    validate_response raises ValueError to trigger exponential backoff retry.
    Succeeds on attempt 3.
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    run_id = await client.trigger_workflow("silent-error-workflow")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    attempt_count = 0

    def step_with_silent_error():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            # Simulate silent API response that didn't raise Exception
            raw_response = {"success": False, "error": "Third party rate limited"}
        else:
            raw_response = {"success": True, "data": "payment_approved"}

        # validate_response checks {"success": False} and converts to retryable ValueError
        return validate_response(raw_response)

    res = await ctx.step("silent-api-step", step_with_silent_error, retries=3, backoff_factor=0.01)
    assert res["success"] is True
    assert res["data"] == "payment_approved"
    assert attempt_count == 3

    await client.close()


@pytest.mark.asyncio
async def test_non_retryable_error_immediate_abort(test_project_key: str):
    """
    Test NonRetryableError Immediate Abort:
    Step raises NonRetryableError (e.g. 401 Unauthorized via validate_response).
    Verifies step immediately aborts without attempting remaining retries.
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    run_id = await client.trigger_workflow("fatal-auth-workflow")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    attempts = 0

    class MockHTTPResponse:
        status_code = 401
        text = "Invalid API Auth Token"

    def fatal_auth_fn():
        nonlocal attempts
        attempts += 1
        # validate_response with raise_non_retryable=True raises NonRetryableError
        return validate_response(MockHTTPResponse(), raise_non_retryable=True)

    with pytest.raises(StepFailedError) as exc_info:
        await ctx.step("fatal-step", fatal_auth_fn, retries=5, backoff_factor=0.01)

    assert "Fatal HTTP Error 401" in str(exc_info.value)
    assert attempts == 1  # Aborted immediately on attempt 1 without wasting 5 retries!

    await client.close()


@pytest.mark.asyncio
async def test_stale_lock_recovery(test_project_key: str):
    """
    Test Lease Lock Timeout & Stale Recovery:
    Worker 1 acquires step lock and crashes (setting locked_until to past).
    Queue engine detects expired lease, recovers step, and allows Worker 2 to complete execution.
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    run_id = await client.trigger_workflow("crash-recovery-workflow")

    # Queue step manually
    step_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "heavy-computation", "max_attempts": 3},
    )
    step_id = step_res.json()["id"]

    # Worker 1 polls and acquires step
    poll_res = await client.http_client.post(
        "/api/v1/steps/poll",
        json={"step_names": ["heavy-computation"], "worker_name": "crashed-worker"},
    )
    assert poll_res.status_code == 200
    assert poll_res.json()["id"] == step_id

    # SIMULATE WORKER 1 CRASH: Expire the lock in DB using ephemeral session
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with TestAsyncSessionLocal() as session:
        await session.execute(
            update(WorkflowStep).where(WorkflowStep.id == step_id).values(locked_until=past_time)
        )
        await session.commit()

    # Worker 2 polls: triggers automatic lock recovery, re-queues step, and acquires it!
    poll_res2 = await client.http_client.post(
        "/api/v1/steps/poll",
        json={"step_names": ["heavy-computation"], "worker_name": "backup-worker"},
    )
    assert poll_res2.status_code == 200
    assert poll_res2.json()["id"] == step_id
    assert poll_res2.json()["attempt_count"] == 2  # Attempt count incremented!

    # Worker 2 completes step
    report_res = await client.http_client.post(
        "/api/v1/steps/report",
        json={"step_id": step_id, "status": "success", "output_payload": {"recovered": True}},
    )
    assert report_res.status_code == 200

    await client.close()


@pytest.mark.asyncio
async def test_targeted_worker_polling(test_project_key: str):
    """
    Test Targeted Step Polling:
    Queue 'send-email' and 'process-payment'.
    Worker polling for 'send-email' receives ONLY 'send-email'.
    """
    client = ApexFlowClient(base_url="http://test", project_key=test_project_key)
    client.http_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-ApexFlow-Project-Key": test_project_key},
    )

    run_id = await client.trigger_workflow("targeted-polling-workflow")

    # Queue step 1: process-payment
    await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "process-payment"},
    )
    # Queue step 2: send-email
    await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "send-email"},
    )

    # Worker registered for ONLY 'send-email' polls
    poll_res = await client.http_client.post(
        "/api/v1/steps/poll",
        json={"step_names": ["send-email"], "worker_name": "email-worker"},
    )
    assert poll_res.status_code == 200
    assert poll_res.json()["step_name"] == "send-email"

    await client.close()
