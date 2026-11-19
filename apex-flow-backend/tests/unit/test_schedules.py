from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from pydantic import ValidationError

from app.core.exceptions import EntityNotFoundException
from app.models.schedule import WorkflowSchedule
from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    WorkerScheduleDeclaration,
)
from app.services.schedules.schedule_service import ScheduleService


def test_schedule_schema_validation_accepts_valid_cron_and_timezone():
    payload = ScheduleCreate(
        workflow_name="  nightly_report  ",
        cron_expression="  0   9 * * 1 ",
        timezone="America/New_York",
        is_active=True,
    )
    assert payload.workflow_name == "nightly_report"
    assert payload.cron_expression == "0 9 * * 1"
    assert payload.timezone == "America/New_York"
    assert payload.is_active is True


@pytest.mark.parametrize(
    "bad_kwargs",
    [
        {"workflow_name": "wf", "cron_expression": "* * *"},
        {"workflow_name": "wf", "cron_expression": "* * * * * *"},
        {"workflow_name": "wf", "cron_expression": "99 * * * *"},
        {"workflow_name": "   ", "cron_expression": "0 0 * * *"},
        {"workflow_name": "wf", "cron_expression": "0 0 * * *", "timezone": "Invalid/Zone"},
        {"workflow_name": "wf", "cron_expression": "0 0 * * *", "extra_field": 123},
    ],
)
def test_schedule_schema_validation_rejects_invalid_inputs(bad_kwargs):
    with pytest.raises(ValidationError):
        ScheduleCreate(**bad_kwargs)


def test_schedule_update_schema_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ScheduleUpdate(cron_expression="0 * * * *", unexpected=True)


def test_calculate_next_run_respects_timezone_and_utc_conversion():
    # 2026-01-15 13:30 UTC is 08:30 AM EST (UTC-5) in America/New_York
    base = datetime(2026, 1, 15, 13, 30, 0, tzinfo=timezone.utc)
    next_run = ScheduleService.calculate_next_run(
        cron_expression="0 9 * * *",
        tz_name="America/New_York",
        base_time=base,
    )
    # Next 09:00 AM EST is 14:00 UTC the same day
    assert next_run.tzinfo == timezone.utc
    assert next_run == datetime(2026, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    # Next 06:00 AM Asia/Dhaka (UTC+6) after 2026-01-15 23:00 UTC (Jan 16 05:00 +06)
    dhaka_base = datetime(2026, 1, 15, 23, 0, 0, tzinfo=timezone.utc)
    next_dhaka = ScheduleService.calculate_next_run(
        cron_expression="0 6 * * *",
        tz_name="Asia/Dhaka",
        base_time=dhaka_base,
    )
    assert next_dhaka == datetime(2026, 1, 16, 0, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_dispatch_due_schedules_triggers_runs_updates_next_run_and_notifies():
    project_id = uuid.uuid4()
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    due_schedule = WorkflowSchedule(
        id=uuid.uuid4(),
        project_id=project_id,
        workflow_name="hourly_cleanup",
        cron_expression="0 * * * *",
        timezone="UTC",
        is_active=True,
        next_run_at=now - timedelta(seconds=10),
        last_run_at=None,
    )

    added_objects = []
    db = AsyncMock()
    db.bind = MagicMock()
    db.bind.dialect.name = "postgresql"
    db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    query_res = MagicMock()
    query_res.scalars.return_value.all.return_value = [due_schedule]
    db.execute.return_value = query_res

    with patch("app.services.schedules.schedule_service.QueueNotifier.notify") as mock_notify:
        dispatched = await ScheduleService.dispatch_due_schedules(db=db, now_override=now)

    assert dispatched == 1
    assert due_schedule.last_run_at == now
    assert due_schedule.next_run_at == datetime(2026, 6, 1, 13, 0, 0, tzinfo=timezone.utc)
    db.commit.assert_awaited_once()
    mock_notify.assert_called_once_with(project_id)

    runs = [obj for obj in added_objects if isinstance(obj, WorkflowRun)]
    steps = [obj for obj in added_objects if isinstance(obj, WorkflowStep)]
    assert len(runs) == 1
    assert len(steps) == 1
    assert runs[0].workflow_name == "hourly_cleanup"
    assert runs[0].metadata_["trigger_source"] == "schedule"
    assert steps[0].step_name == "hourly_cleanup"
    assert steps[0].step_order == 0
    assert steps[0].workflow_run_id == runs[0].id


@pytest.mark.asyncio
async def test_dispatch_due_schedules_noop_when_none_due():
    db = AsyncMock()
    db.bind = MagicMock()
    db.bind.dialect.name = "postgresql"

    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []
    db.execute.return_value = empty_res

    with patch("app.services.schedules.schedule_service.QueueNotifier.notify") as mock_notify:
        dispatched = await ScheduleService.dispatch_due_schedules(db=db)

    assert dispatched == 0
    db.commit.assert_not_awaited()
    mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_create_schedule_duplicate_workflow_raises_value_error():
    project_id = uuid.uuid4()
    db = AsyncMock()
    existing_res = MagicMock()
    existing_res.scalar_one_or_none.return_value = WorkflowSchedule(
        id=uuid.uuid4(),
        project_id=project_id,
        workflow_name="dup_flow",
        cron_expression="0 * * * *",
        timezone="UTC",
        is_active=True,
    )
    db.execute.return_value = existing_res

    with pytest.raises(ValueError, match="already exists"):
        await ScheduleService.create_schedule(
            db=db,
            project_id=project_id,
            payload=ScheduleCreate(workflow_name="dup_flow", cron_expression="*/5 * * * *"),
        )


@pytest.mark.asyncio
async def test_pause_resume_and_trigger_run_now():
    project_id = uuid.uuid4()
    schedule_id = uuid.uuid4()
    future_next = datetime.now(timezone.utc) + timedelta(hours=2)
    schedule = WorkflowSchedule(
        id=schedule_id,
        project_id=project_id,
        workflow_name="billing_job",
        cron_expression="0 */6 * * *",
        timezone="UTC",
        is_active=True,
        next_run_at=future_next,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = schedule
    db.execute.return_value = res

    paused = await ScheduleService.pause_schedule(
        db=db, project_id=project_id, schedule_id=schedule_id
    )
    assert paused.is_active is False
    assert paused.next_run_at is None

    resumed = await ScheduleService.resume_schedule(
        db=db, project_id=project_id, schedule_id=schedule_id
    )
    assert resumed.is_active is True
    assert resumed.next_run_at is not None
    scheduled_next_before_manual = resumed.next_run_at

    with patch("app.services.schedules.schedule_service.QueueNotifier.notify") as mock_notify:
        updated_sched, manual_run = await ScheduleService.trigger_run_now(
            db=db, project_id=project_id, schedule_id=schedule_id
        )

    assert updated_sched.last_run_at is not None
    assert updated_sched.next_run_at == scheduled_next_before_manual
    assert manual_run.workflow_name == "billing_job"
    assert manual_run.metadata_["trigger_source"] == "schedule_manual"
    mock_notify.assert_called_once_with(project_id)


@pytest.mark.asyncio
async def test_sync_worker_schedules_preserves_paused_status_on_existing_schedule():
    project_id = uuid.uuid4()
    paused_existing = WorkflowSchedule(
        id=uuid.uuid4(),
        project_id=project_id,
        workflow_name="paused_sync_job",
        cron_expression="0 * * * *",
        timezone="UTC",
        is_active=False,
        next_run_at=None,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = paused_existing
    db.execute.return_value = res

    synced = await ScheduleService.sync_worker_schedules(
        db=db,
        project_id=project_id,
        declarations=[
            WorkerScheduleDeclaration(
                workflow_name="paused_sync_job",
                cron_expression="*/15 * * * *",
                timezone="UTC",
            )
        ],
    )

    assert len(synced) == 1
    assert synced[0].cron_expression == "*/15 * * * *"
    assert synced[0].is_active is False
    assert synced[0].next_run_at is None
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_schedule_by_id_missing_raises_not_found():
    db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    db.execute.return_value = res

    with pytest.raises(EntityNotFoundException):
        await ScheduleService.get_schedule_by_id(
            db=db,
            project_id=uuid.uuid4(),
            schedule_id=uuid.uuid4(),
        )

