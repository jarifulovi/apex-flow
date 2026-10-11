import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.step import WorkflowStepCreate
from app.schemas.workflow import WorkflowCreate
from app.services.steps.queue_service import QueueService
from app.services.steps.step_service import StepService
from app.services.workflows.workflow_service import WorkflowService


@pytest.mark.asyncio
async def test_create_workflow_with_debounce_sets_debounced_until():
    """Verify that creating a workflow with debounce_seconds calculates debounced_until."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    # No existing debounced or deduplicated run
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res

    proj_id = uuid.uuid4()
    payload = WorkflowCreate(
        project_id=proj_id,
        workflow_name="image-processing-job",
        deduplication_id="img-upload-999",
        debounce_seconds=10,
        max_debounce_seconds=60,
        metadata={"file": "test.jpg"},
    )

    run = await WorkflowService.create_workflow_run(db=db, payload=payload, project_id=proj_id)

    assert run.workflow_name == "image-processing-job"
    assert run.deduplication_id == "img-upload-999"
    assert run.debounce_seconds == 10
    assert run.status == "pending"
    assert run.debounced_until is not None
    assert run.debounce_deadline_at is not None
    assert run.debounced_until > datetime.now(timezone.utc)
    assert run.debounce_deadline_at > run.debounced_until
    db.add.assert_called_once_with(run)


@pytest.mark.asyncio
async def test_subsequent_trigger_within_debounce_window_coalesces_and_extends():
    """Verify that an incoming trigger during an active debounce window coalesces and extends the delay."""
    db = AsyncMock()
    db.refresh = AsyncMock()

    now = datetime.now(timezone.utc)
    existing_run = WorkflowRun(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        workflow_name="doc-indexer",
        deduplication_id="doc-42",
        status="pending",
        metadata_={"v": 1, "source": "webhook"},
        debounce_seconds=5,
        debounced_until=now + timedelta(seconds=4),
        debounce_deadline_at=now + timedelta(seconds=30),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_run
    db.execute.return_value = mock_res

    # Second event fires with updated metadata and 10s debounce
    payload = WorkflowCreate(
        project_id=existing_run.project_id,
        workflow_name="doc-indexer",
        deduplication_id="doc-42",
        debounce_seconds=10,
        metadata={"v": 2, "updated_by": "alice"},
    )

    returned_run = await WorkflowService.create_workflow_run(
        db=db, payload=payload, project_id=existing_run.project_id
    )

    assert returned_run.id == existing_run.id
    assert returned_run.debounce_seconds == 10
    # Window extended to ~now + 10s
    assert returned_run.debounced_until > now + timedelta(seconds=8)
    # Metadata merged
    assert returned_run.metadata_ == {"v": 2, "source": "webhook", "updated_by": "alice"}
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_debounce_respects_max_debounce_deadline():
    """Verify that repeated bounces cannot extend past the absolute debounce_deadline_at."""
    db = AsyncMock()
    db.refresh = AsyncMock()

    now = datetime.now(timezone.utc)
    hard_deadline = now + timedelta(seconds=7)
    existing_run = WorkflowRun(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        workflow_name="sensor-data-sink",
        deduplication_id="sensor-node-1",
        status="pending",
        metadata_={"reading": 1},
        debounce_seconds=5,
        debounced_until=now + timedelta(seconds=3),
        debounce_deadline_at=hard_deadline,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_run
    db.execute.return_value = mock_res

    # Event arrives wanting 15 seconds extension, but hard deadline is 7 seconds
    payload = WorkflowCreate(
        project_id=existing_run.project_id,
        workflow_name="sensor-data-sink",
        deduplication_id="sensor-node-1",
        debounce_seconds=15,
        metadata={"reading": 2},
    )

    returned_run = await WorkflowService.create_workflow_run(
        db=db, payload=payload, project_id=existing_run.project_id
    )

    assert returned_run.id == existing_run.id
    # Window must be capped at hard_deadline
    assert returned_run.debounced_until == hard_deadline


@pytest.mark.asyncio
async def test_anonymous_debounce_coalesces_by_workflow_name():
    """Verify that multiple triggers without deduplication_id coalesce by workflow_name during debounce."""
    db = AsyncMock()
    db.refresh = AsyncMock()

    now = datetime.now(timezone.utc)
    proj_id = uuid.uuid4()
    existing_run = WorkflowRun(
        id=uuid.uuid4(),
        project_id=proj_id,
        workflow_name="batch-cache-invalidation",
        deduplication_id=None,
        status="pending",
        metadata_={"tags": ["products"]},
        debounce_seconds=5,
        debounced_until=now + timedelta(seconds=4),
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_run
    db.execute.return_value = mock_res

    # Second trigger with no deduplication_id
    payload = WorkflowCreate(
        project_id=proj_id,
        workflow_name="batch-cache-invalidation",
        debounce_seconds=5,
        metadata={"tags": ["categories"]},
    )

    returned_run = await WorkflowService.create_workflow_run(db=db, payload=payload, project_id=proj_id)

    assert returned_run.id == existing_run.id
    assert returned_run.metadata_ == {"tags": ["categories"]}


@pytest.mark.asyncio
async def test_step_creation_defers_availability_to_debounced_until():
    """Verify that queueing a step on an actively debouncing workflow defers available_at and keeps workflow pending."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    debounced_time = now + timedelta(seconds=20)

    # Mock query fetching parent workflow's priority and debounced_until
    mock_parent_res = MagicMock()
    mock_parent_res.first.return_value = (5, debounced_time)
    mock_parent_res.one_or_none.return_value = (5, debounced_time)
    db.execute.return_value = mock_parent_res

    payload = WorkflowStepCreate(
        workflow_id=run_id,
        step_name="process_debounced_items",
        priority=0,
    )

    step = await StepService.create_step(db=db, payload=payload)

    assert step.step_name == "process_debounced_items"
    assert step.priority == 5
    # Step available_at must be held back to debounced_time
    assert step.available_at == debounced_time
