import asyncio
from datetime import datetime, timedelta, timezone
import time
from unittest.mock import patch
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import WorkflowSchedule
from app.services.housekeeping import HousekeepingService
from app.services.schedules import ScheduleService
from app.services.steps.notifier import QueueNotifier
from apex_flow_sdk import ApexFlowClient, WorkflowContext
from tests.conftest import TestAsyncSessionLocal
from tests.helpers.assertions import ApexFlowAssert


@pytest.mark.asyncio
async def test_e2e_worker_schedule_sync_and_cron_ticker_dispatch(
    test_client_harness: ApexFlowClient,
    test_project,
    db: AsyncSession,
):
    """
    End-to-end happy path for cron scheduling:
    1. Worker declares @client.workflow(..., cron=...) and syncs schedule on startup.
    2. HousekeepingService ticker detects the due schedule via FOR UPDATE SKIP LOCKED.
    3. Dispatcher creates WorkflowRun + entrypoint step, advances next_run_at, and notifies worker.
    4. Worker wakes via QueueNotifier, executes inner ctx.step calls, and completes the run.
    """
    client = test_client_harness
    executed_runs = []
    executed_event = asyncio.Event()

    @client.workflow("scheduled-etl-pipeline", cron="*/5 * * * *", timezone="UTC")
    async def scheduled_etl_pipeline(ctx: WorkflowContext):
        extracted = await ctx.step("extract", lambda: {"rows": 10})
        loaded = await ctx.step("load", lambda: {"written": extracted["rows"]})
        executed_runs.append(ctx.workflow_run_id)
        executed_event.set()
        return loaded

    worker_task = asyncio.create_task(
        client.start_worker(
            poll_timeout=20.0,
            run_once=False,
        )
    )

    try:
        # 1. Wait for worker startup sync + long-poll registration
        wait_deadline = time.monotonic() + 30.0
        while not QueueNotifier.is_waiting(test_project.id) and time.monotonic() < wait_deadline:
            await asyncio.sleep(0.1)
        assert QueueNotifier.is_waiting(test_project.id) is True

        # 2. Verify schedule exists via REST API
        list_res = await client.http_client.get(f"/api/v1/projects/{test_project.id}/schedules")
        assert list_res.status_code == 200
        schedules = list_res.json()
        assert len(schedules) == 1
        schedule_id = schedules[0]["id"]
        assert schedules[0]["workflow_name"] == "scheduled-etl-pipeline"
        assert schedules[0]["cron_expression"] == "*/5 * * * *"
        assert schedules[0]["is_active"] is True
        assert schedules[0]["next_run_at"] is not None

        # 3. Force schedule due and invoke HousekeepingService ticker
        past_due = datetime.now(timezone.utc) - timedelta(seconds=5)
        await db.execute(
            update(WorkflowSchedule)
            .where(WorkflowSchedule.project_id == test_project.id)
            .values(next_run_at=past_due)
        )
        await db.commit()

        before_sweep = datetime.now(timezone.utc)
        with patch(
            "app.services.housekeeping.housekeeping_service.AsyncSessionLocal",
            TestAsyncSessionLocal,
        ):
            await HousekeepingService.run_sweep()

        # 4. Wait for worker to finish workflow steps, then verify completion & step states
        await asyncio.wait_for(executed_event.wait(), timeout=90.0)
        assert len(executed_runs) == 1
        dispatched_run_id = executed_runs[0]

        complete_deadline = time.monotonic() + 60.0
        completed_run = None
        last_observed = None
        while time.monotonic() < complete_deadline:
            detail_res = await client.http_client.get(f"/api/v1/workflows/{dispatched_run_id}")
            assert detail_res.status_code == 200
            candidate = detail_res.json()
            last_observed = candidate
            if (
                candidate["status"] == "completed"
                and candidate["steps"]
                and all(step["status"] == "success" for step in candidate["steps"])
            ):
                completed_run = candidate
                break
            await asyncio.sleep(1.0)

        assert completed_run is not None, f"Scheduled run did not finalize cleanly: {last_observed}"
        ApexFlowAssert.assert_workflow_run(
            completed_run,
            workflow_name="scheduled-etl-pipeline",
            status="completed",
            completed_at=True,
        )
        assert completed_run["metadata_"]["trigger_source"] == "schedule"
        assert completed_run["metadata_"]["schedule_id"] == schedule_id

        step_names = {s["step_name"] for s in completed_run["steps"]}
        assert {"extract", "load"}.issubset(step_names)
        for step in completed_run["steps"]:
            ApexFlowAssert.assert_step(step, status="success")

        # 5. Confirm schedule advanced next_run_at and recorded last_run_at
        sched_res = await client.http_client.get(
            f"/api/v1/projects/{test_project.id}/schedules/{schedule_id}"
        )
        assert sched_res.status_code == 200
        sched_data = sched_res.json()
        assert sched_data["last_run_at"] is not None
        next_run_dt = datetime.fromisoformat(sched_data["next_run_at"].replace("Z", "+00:00"))
        assert next_run_dt > before_sweep
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_e2e_schedule_lifecycle_crud_pause_resume_and_run_now(
    test_client_harness: ApexFlowClient,
    test_project,
    db: AsyncSession,
):
    """
    End-to-end happy path for schedule REST management:
    create -> update -> pause (blocks ticker) -> resume -> manual Run Now (executes on worker) -> delete.
    """
    client = test_client_harness

    # 1. Create schedule via REST API
    create_res = await client.http_client.post(
        f"/api/v1/projects/{test_project.id}/schedules",
        json={
            "workflow_name": "manual-cron-job",
            "cron_expression": "0 12 * * *",
            "timezone": "UTC",
            "is_active": True,
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    schedule_id = created["id"]
    assert created["cron_expression"] == "0 12 * * *"
    assert created["is_active"] is True
    assert created["next_run_at"] is not None

    # 2. Update cron & timezone
    patch_res = await client.http_client.patch(
        f"/api/v1/projects/{test_project.id}/schedules/{schedule_id}",
        json={"cron_expression": "30 8 * * 1-5", "timezone": "America/New_York"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["cron_expression"] == "30 8 * * 1-5"
    assert patch_res.json()["timezone"] == "America/New_York"

    # 3. Pause schedule and verify ticker does not dispatch
    pause_res = await client.http_client.post(
        f"/api/v1/projects/{test_project.id}/schedules/{schedule_id}/pause"
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["is_active"] is False
    assert pause_res.json()["next_run_at"] is None

    dispatched_while_paused = await ScheduleService.dispatch_due_schedules(
        db=db,
        project_id=test_project.id,
        now_override=datetime.now(timezone.utc) + timedelta(days=2),
    )
    assert dispatched_while_paused == 0

    # 4. Resume schedule
    resume_res = await client.http_client.post(
        f"/api/v1/projects/{test_project.id}/schedules/{schedule_id}/resume"
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["is_active"] is True
    scheduled_next_before_run = resume_res.json()["next_run_at"]
    assert scheduled_next_before_run is not None

    # 5. Start worker & trigger "Run Now"
    manual_executed_event = asyncio.Event()

    @client.workflow("manual-cron-job")
    async def manual_cron_job(ctx: WorkflowContext):
        result = await ctx.step("run-task", lambda: {"triggered": "manual"})
        manual_executed_event.set()
        return result

    worker_task = asyncio.create_task(client.start_worker(poll_timeout=20.0, run_once=False))
    try:
        wait_deadline = time.monotonic() + 30.0
        while not QueueNotifier.is_waiting(test_project.id) and time.monotonic() < wait_deadline:
            await asyncio.sleep(0.1)

        run_now_res = await client.http_client.post(
            f"/api/v1/projects/{test_project.id}/schedules/{schedule_id}/run"
        )
        assert run_now_res.status_code == 200
        trigger_data = run_now_res.json()
        manual_run_id = trigger_data["workflow_run_id"]
        assert trigger_data["schedule"]["last_run_at"] is not None
        assert trigger_data["schedule"]["next_run_at"] == scheduled_next_before_run

        await asyncio.wait_for(manual_executed_event.wait(), timeout=60.0)

        # Wait for manual run completion and dispatch step reporting
        complete_deadline = time.monotonic() + 60.0
        manual_run_detail = None
        last_manual_observed = None
        while time.monotonic() < complete_deadline:
            wf_res = await client.http_client.get(f"/api/v1/workflows/{manual_run_id}")
            assert wf_res.status_code == 200
            candidate = wf_res.json()
            last_manual_observed = candidate
            if (
                candidate["status"] == "completed"
                and candidate["steps"]
                and all(step["status"] == "success" for step in candidate["steps"])
            ):
                manual_run_detail = candidate
                break
            await asyncio.sleep(1.0)

        assert manual_run_detail is not None, f"Manual run did not finalize cleanly: {last_manual_observed}"
        ApexFlowAssert.assert_workflow_run(
            manual_run_detail,
            workflow_name="manual-cron-job",
            status="completed",
        )
        assert manual_run_detail["metadata_"]["trigger_source"] == "schedule_manual"
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    # 6. Delete schedule and verify list is empty
    delete_res = await client.http_client.delete(
        f"/api/v1/projects/{test_project.id}/schedules/{schedule_id}"
    )
    assert delete_res.status_code == 204

    list_after_del = await client.http_client.get(
        f"/api/v1/projects/{test_project.id}/schedules"
    )
    assert list_after_del.status_code == 200
    assert list_after_del.json() == []

    # Verify DB deletion cleanly committed
    db_row = (
        await db.execute(select(WorkflowSchedule).where(WorkflowSchedule.id == schedule_id))
    ).scalar_one_or_none()
    assert db_row is None

