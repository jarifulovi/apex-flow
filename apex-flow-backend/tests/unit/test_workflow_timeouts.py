import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from pydantic import ValidationError

from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.workflow import WorkflowCreate
from app.services.steps.queue_service import QueueService
from app.services.workflows.workflow_service import WorkflowService


@pytest.mark.asyncio
async def test_create_workflow_run_with_timeout_computes_deadline_at():
    """Verify create_workflow_run computes deadline_at when timeout_seconds is provided."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    payload = WorkflowCreate(
        workflow_name="timeout_workflow",
        timeout_seconds=120,
    )

    before_create = datetime.now(timezone.utc)
    wf = await WorkflowService.create_workflow_run(
        db=db, payload=payload, project_id=uuid.uuid4()
    )
    after_create = datetime.now(timezone.utc)

    assert wf.workflow_name == "timeout_workflow"
    assert wf.status == "pending"
    assert wf.timeout_seconds == 120
    assert wf.deadline_at is not None
    assert before_create + timedelta(seconds=120) <= wf.deadline_at <= after_create + timedelta(seconds=120)
    db.add.assert_called_once_with(wf)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_workflow_run_without_timeout_has_no_deadline():
    """Verify create_workflow_run leaves deadline_at None when timeout_seconds is not passed."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    payload = WorkflowCreate(workflow_name="unlimited_workflow")
    wf = await WorkflowService.create_workflow_run(
        db=db, payload=payload, project_id=uuid.uuid4()
    )

    assert wf.timeout_seconds is None
    assert wf.deadline_at is None
    db.add.assert_called_once_with(wf)


@pytest.mark.asyncio
async def test_recover_timed_out_workflows_marks_failed_and_cancels_steps():
    """Verify recover_timed_out_workflows fails expired runs and cancels queued/running steps."""
    db = AsyncMock()
    db.bind = MagicMock()
    db.bind.dialect.name = "postgresql"

    project_id = uuid.uuid4()
    run_id = uuid.uuid4()

    expired_run = WorkflowRun(
        id=run_id,
        project_id=project_id,
        workflow_name="hung_workflow",
        status="running",
        timeout_seconds=60,
        deadline_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [expired_run]
    db.execute.return_value = mock_result

    before_recovery = datetime.now(timezone.utc)
    count = await QueueService.recover_timed_out_workflows(db=db, project_id=project_id)
    after_recovery = datetime.now(timezone.utc)

    assert count == 1
    assert expired_run.status == "failed"
    assert before_recovery <= expired_run.completed_at <= after_recovery
    assert "Workflow execution timed out (exceeded 60s limit)" in expired_run.error_message
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_workflow_run_by_id_proactively_enforces_timeout():
    """Verify get_workflow_run_by_id detects expired deadline and marks run failed immediately."""
    db = AsyncMock()
    run_id = uuid.uuid4()

    expired_run = WorkflowRun(
        id=run_id,
        project_id=uuid.uuid4(),
        workflow_name="api_queried_run",
        status="running",
        timeout_seconds=30,
        deadline_at=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    # Child step currently running
    child_step = WorkflowStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        step_name="step_in_progress",
        status="running",
    )
    expired_run.steps = [child_step]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expired_run

    mock_sub_res = MagicMock()
    mock_sub_res.scalars.return_value.all.return_value = []

    db.execute.side_effect = [mock_result, mock_sub_res]
    db.refresh = AsyncMock()

    wf = await WorkflowService.get_workflow_run_by_id(db=db, workflow_run_id=run_id)

    assert wf.status == "failed"
    assert "Workflow execution timed out (exceeded 30s limit)" in wf.error_message
    assert child_step.status == "cancelled"
    assert child_step.error_message == "Cancelled due to workflow timeout."
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_restart_workflow_run_recomputes_deadline_at():
    """Verify restart_workflow_run clears failure error and recomputes deadline_at from now."""
    db = AsyncMock()
    run_id = uuid.uuid4()

    failed_run = WorkflowRun(
        id=run_id,
        project_id=uuid.uuid4(),
        workflow_name="retry_run",
        status="failed",
        error_message="Previous failure",
        timeout_seconds=45,
        deadline_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    failed_step = WorkflowStep(
        id=uuid.uuid4(),
        workflow_run_id=run_id,
        step_name="failed_step",
        status="failed",
    )
    failed_run.steps = [failed_step]

    # Mock get_workflow_run_by_id internals
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = failed_run
    mock_sub_res = MagicMock()
    mock_sub_res.scalars.return_value.all.return_value = []
    db.execute.side_effect = [mock_result, mock_sub_res, MagicMock()]
    db.refresh = AsyncMock()

    before_restart = datetime.now(timezone.utc)
    restarted_wf = await WorkflowService.restart_workflow_run(db=db, workflow_run_id=run_id)
    after_restart = datetime.now(timezone.utc)

    assert restarted_wf.status == "running"
    assert restarted_wf.error_message is None
    assert before_restart + timedelta(seconds=45) <= restarted_wf.deadline_at <= after_restart + timedelta(seconds=45)
    assert failed_step.status == "queued"
    assert failed_step.error_message is None


def test_workflow_schema_validation_timeout():
    """Verify WorkflowCreate schema enforces valid positive timeout_seconds limits."""
    # Valid timeout
    wf_valid = WorkflowCreate(workflow_name="ok", timeout_seconds=60)
    assert wf_valid.timeout_seconds == 60

    # Reject non-positive timeout (ge=1)
    with pytest.raises(ValidationError):
        WorkflowCreate(workflow_name="bad", timeout_seconds=0)

    with pytest.raises(ValidationError):
        WorkflowCreate(workflow_name="bad", timeout_seconds=-10)

    # Reject timeout exceeding 30 days
    with pytest.raises(ValidationError):
        WorkflowCreate(workflow_name="bad", timeout_seconds=86400 * 31)
