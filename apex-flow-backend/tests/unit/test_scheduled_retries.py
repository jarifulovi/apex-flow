import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from pydantic import ValidationError

from app.models.step import WorkflowStep
from app.schemas.step import StepReportPayload, StepStatus, WorkflowStepCreate
from app.services.steps.queue_service import QueueService
from app.services.steps.step_service import StepService


@pytest.mark.asyncio
async def test_create_step_with_delay_sets_future_available_at():
    """Verify that creating a step with delay_seconds sets available_at in the future."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    payload = WorkflowStepCreate(
        workflow_id=uuid.uuid4(),
        step_name="delayed_task",
        delay_seconds=45,
    )

    before_create = datetime.now(timezone.utc)
    step = await StepService.create_step(db=db, payload=payload)
    after_create = datetime.now(timezone.utc)

    assert step.step_name == "delayed_task"
    assert step.status == "queued"
    assert step.available_at >= before_create + timedelta(seconds=45)
    assert step.available_at <= after_create + timedelta(seconds=45)
    db.add.assert_called_once_with(step)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_step_without_delay_sets_available_at_now():
    """Verify that creating a step without delay defaults available_at to now."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    payload = WorkflowStepCreate(
        workflow_id=uuid.uuid4(),
        step_name="immediate_task",
    )

    before_create = datetime.now(timezone.utc)
    step = await StepService.create_step(db=db, payload=payload)
    after_create = datetime.now(timezone.utc)

    assert step.step_name == "immediate_task"
    assert step.status == "queued"
    assert before_create <= step.available_at <= after_create
    db.add.assert_called_once_with(step)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_report_step_failure_exponential_backoff():
    """Verify that failed steps with remaining attempts get scheduled with exponential backoff."""
    db = AsyncMock()
    step_id = uuid.uuid4()
    run_id = uuid.uuid4()

    # Step on attempt 1 of 3
    existing_step = WorkflowStep(
        id=step_id,
        workflow_run_id=run_id,
        step_name="failing_task",
        status="running",
        attempt_count=1,
        max_attempts=3,
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_step
    db.execute.return_value = mock_result
    db.refresh = AsyncMock()

    before_report = datetime.now(timezone.utc)
    report_payload = StepReportPayload(
        step_id=step_id,
        status=StepStatus.FAILED,
        attempt_count=1,
        error_message="Network glitch",
    )

    updated_step = await StepService.report_step_status(db=db, payload=report_payload)

    # Status must be queued and locked_until released
    assert updated_step.status == "queued"
    assert updated_step.locked_until is None
    # Attempt 1: 2^(1-1) = 1s backoff
    assert updated_step.available_at >= before_report + timedelta(seconds=1)
    assert updated_step.available_at <= datetime.now(timezone.utc) + timedelta(seconds=2)


@pytest.mark.asyncio
async def test_report_step_failure_attempt_2_exponential_backoff():
    """Verify backoff grows exponentially: attempt 2 gives 2s delay."""
    db = AsyncMock()
    step_id = uuid.uuid4()
    run_id = uuid.uuid4()

    existing_step = WorkflowStep(
        id=step_id,
        workflow_run_id=run_id,
        step_name="failing_task",
        status="running",
        attempt_count=2,
        max_attempts=3,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_step
    db.execute.return_value = mock_result
    db.refresh = AsyncMock()

    before_report = datetime.now(timezone.utc)
    report_payload = StepReportPayload(
        step_id=step_id,
        status=StepStatus.FAILED,
        attempt_count=2,
        error_message="Second error",
    )

    updated_step = await StepService.report_step_status(db=db, payload=report_payload)

    assert updated_step.status == "queued"
    # Attempt 2: 2^(2-1) = 2s backoff
    assert updated_step.available_at >= before_report + timedelta(seconds=2)
    assert updated_step.available_at <= datetime.now(timezone.utc) + timedelta(seconds=3)


@pytest.mark.asyncio
async def test_report_step_failure_custom_retry_delay():
    """Verify that reporting a failure with explicit retry_delay_seconds overrides default backoff."""
    db = AsyncMock()
    step_id = uuid.uuid4()
    run_id = uuid.uuid4()

    existing_step = WorkflowStep(
        id=step_id,
        workflow_run_id=run_id,
        step_name="rate_limited_task",
        status="running",
        attempt_count=1,
        max_attempts=5,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_step
    db.execute.return_value = mock_result
    db.refresh = AsyncMock()

    before_report = datetime.now(timezone.utc)
    report_payload = StepReportPayload(
        step_id=step_id,
        status=StepStatus.FAILED,
        attempt_count=1,
        error_message="HTTP 429 Too Many Requests",
        retry_delay_seconds=60,
    )

    updated_step = await StepService.report_step_status(db=db, payload=report_payload)

    assert updated_step.status == "queued"
    assert updated_step.available_at >= before_report + timedelta(seconds=60)
    assert updated_step.available_at <= datetime.now(timezone.utc) + timedelta(seconds=62)


@pytest.mark.asyncio
async def test_report_step_failure_exhausted_attempts():
    """Verify that exhausting max_attempts marks the step permanently failed."""
    db = AsyncMock()
    step_id = uuid.uuid4()
    run_id = uuid.uuid4()

    existing_step = WorkflowStep(
        id=step_id,
        workflow_run_id=run_id,
        step_name="permanently_failing_task",
        status="running",
        attempt_count=3,
        max_attempts=3,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_step
    db.execute.return_value = mock_result
    db.refresh = AsyncMock()

    report_payload = StepReportPayload(
        step_id=step_id,
        status=StepStatus.FAILED,
        attempt_count=3,
        error_message="Out of retries",
    )

    updated_step = await StepService.report_step_status(db=db, payload=report_payload)

    assert updated_step.status == "failed"
    assert updated_step.completed_at is not None


@pytest.mark.asyncio
async def test_recover_stale_locks_resets_available_at_to_now():
    """Verify that recovering stale locks resets available_at to now for re-queued steps."""
    db = AsyncMock()
    db.bind = MagicMock()
    db.bind.dialect.name = "postgresql"

    project_id = uuid.uuid4()
    stale_step = WorkflowStep(
        id=uuid.uuid4(),
        workflow_run_id=uuid.uuid4(),
        step_name="worker_crashed_task",
        status="running",
        attempt_count=1,
        max_attempts=3,
        locked_until=datetime.now(timezone.utc) - timedelta(minutes=5),
        available_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [stale_step]
    db.execute.return_value = mock_result

    before_recovery = datetime.now(timezone.utc)
    recovered_count = await QueueService.recover_stale_locks(db=db, project_id=project_id)
    after_recovery = datetime.now(timezone.utc)

    assert recovered_count == 1
    assert stale_step.status == "queued"
    assert stale_step.locked_until is None
    assert before_recovery <= stale_step.available_at <= after_recovery


def test_schema_validations_for_delays():
    """Verify Pydantic schema validation on delay fields."""
    valid_step = WorkflowStepCreate(
        workflow_id=uuid.uuid4(),
        step_name="test",
        delay_seconds=30,
    )
    assert valid_step.delay_seconds == 30

    with pytest.raises(ValidationError):
        WorkflowStepCreate(
            workflow_id=uuid.uuid4(),
            step_name="test",
            delay_seconds=-5,  # Must be >= 0
        )

    valid_report = StepReportPayload(
        step_id=uuid.uuid4(),
        status=StepStatus.FAILED,
        retry_delay_seconds=15,
    )
    assert valid_report.retry_delay_seconds == 15

    with pytest.raises(ValidationError):
        StepReportPayload(
            step_id=uuid.uuid4(),
            status=StepStatus.FAILED,
            retry_delay_seconds=-1,  # Must be >= 0
        )
