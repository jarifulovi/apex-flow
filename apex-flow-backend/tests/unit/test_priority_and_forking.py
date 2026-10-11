import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from pydantic import ValidationError

from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.step import WorkflowStepCreate
from app.schemas.workflow import WorkflowCreate, WorkflowForkRequest
from app.services.steps.step_service import StepService
from app.services.workflows.workflow_service import WorkflowService


@pytest.mark.asyncio
async def test_step_inherits_parent_workflow_priority():
    """Verify that creating a step inherits parent workflow priority when step priority is 0."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    run_id = uuid.uuid4()
    # Mock query fetching parent workflow priority (-10)
    mock_priority_res = MagicMock()
    mock_priority_res.scalar_one_or_none.return_value = -10
    db.execute.return_value = mock_priority_res

    payload = WorkflowStepCreate(
        workflow_id=run_id,
        step_name="urgent_child_step",
        priority=0,  # Default, should inherit parent
    )

    step = await StepService.create_step(db=db, payload=payload)

    assert step.step_name == "urgent_child_step"
    assert step.priority == -10
    db.add.assert_called_once_with(step)


@pytest.mark.asyncio
async def test_step_can_override_workflow_priority():
    """Verify that explicitly passing a non-zero priority overrides parent workflow priority."""
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()

    run_id = uuid.uuid4()
    payload = WorkflowStepCreate(
        workflow_id=run_id,
        step_name="custom_override_step",
        priority=25,  # Explicitly low priority
    )

    step = await StepService.create_step(db=db, payload=payload)

    assert step.step_name == "custom_override_step"
    assert step.priority == 25


@pytest.mark.asyncio
async def test_fork_workflow_run_at_step_3():
    """Verify workflow forking clones prior steps as memoized checkpoints and queues the fork step."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    project_id = uuid.uuid4()
    source_run_id = uuid.uuid4()

    source_run = WorkflowRun(
        id=source_run_id,
        project_id=project_id,
        workflow_name="original_pipeline",
        status="failed",
        priority=-5,
        timeout_seconds=300,
        metadata_={"environment": "production"},
    )

    # 4 historical steps
    s1 = WorkflowStep(
        id=uuid.uuid4(),
        workflow_run_id=source_run_id,
        step_name="fetch_user",
        step_order=1,
        status="success",
        input_payload={"user_id": 42},
        output_payload={"user_name": "Alice"},
    )
    s2 = WorkflowStep(
        id=uuid.uuid4(),
        workflow_run_id=source_run_id,
        step_name="fetch_orders",
        step_order=2,
        status="success",
        input_payload={"user_name": "Alice"},
        output_payload={"orders_count": 5},
    )
    s3 = WorkflowStep(
        id=uuid.uuid4(),
        workflow_run_id=source_run_id,
        step_name="generate_invoice",
        step_order=3,
        status="failed",
        error_message="Payment gateway error",
        input_payload={"orders_count": 5},
        output_payload={},
    )
    s4 = WorkflowStep(
        id=uuid.uuid4(),
        workflow_run_id=source_run_id,
        step_name="send_email",
        step_order=4,
        status="cancelled",
        input_payload={},
        output_payload={},
    )
    source_run.steps = [s1, s2, s3, s4]

    # Mock get_workflow_run_by_id calls
    mock_run_res = MagicMock()
    mock_run_res.scalar_one_or_none.return_value = source_run
    mock_sub_res = MagicMock()
    mock_sub_res.scalars.return_value.all.return_value = []
    db.execute.side_effect = [mock_run_res, mock_sub_res, mock_run_res, mock_sub_res]

    # Fork at step 3
    forked_run = await WorkflowService.fork_workflow_run(
        db=db,
        workflow_run_id=source_run_id,
        from_step_order=3,
        new_name="forked_pipeline",
    )

    # Verify forked run metadata and relationship
    added_objects = [call.args[0] for call in db.add.call_args_list]
    forked_run_obj = [obj for obj in added_objects if isinstance(obj, WorkflowRun)][0]
    cloned_steps = [obj for obj in added_objects if isinstance(obj, WorkflowStep)]

    assert forked_run_obj.workflow_name == "forked_pipeline"
    assert forked_run_obj.forked_from_id == source_run_id
    assert forked_run_obj.status == "pending"
    assert forked_run_obj.priority == -5
    assert forked_run_obj.timeout_seconds == 300

    # Steps 1 and 2 should be cloned as completed checkpoints with memoized output
    assert len(cloned_steps) == 3  # Steps 1, 2, and 3
    cloned_s1 = [s for s in cloned_steps if s.step_order == 1][0]
    cloned_s2 = [s for s in cloned_steps if s.step_order == 2][0]
    cloned_s3 = [s for s in cloned_steps if s.step_order == 3][0]

    assert cloned_s1.status == "success"
    assert cloned_s1.output_payload == {"user_name": "Alice"}

    assert cloned_s2.status == "success"
    assert cloned_s2.output_payload == {"orders_count": 5}

    # Step 3 must be queued for fresh execution
    assert cloned_s3.status == "queued"
    assert cloned_s3.attempt_count == 0
    assert cloned_s3.output_payload == {}
    assert cloned_s3.error_message is None


@pytest.mark.asyncio
async def test_fork_workflow_run_rewind_to_step_2():
    """Verify rewinding: forking at step 2 queues step 2 and only memoizes step 1."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    source_run = WorkflowRun(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        workflow_name="pipeline",
        status="failed",
        priority=0,
        metadata_={},
    )
    s1 = WorkflowStep(id=uuid.uuid4(), step_name="step_1", step_order=1, status="success", input_payload={}, output_payload={"val": 1})
    s2 = WorkflowStep(id=uuid.uuid4(), step_name="step_2", step_order=2, status="failed", input_payload={}, output_payload={})
    s3 = WorkflowStep(id=uuid.uuid4(), step_name="step_3", step_order=3, status="cancelled", input_payload={}, output_payload={})
    source_run.steps = [s1, s2, s3]

    mock_run_res = MagicMock()
    mock_run_res.scalar_one_or_none.return_value = source_run
    mock_sub_res = MagicMock()
    mock_sub_res.scalars.return_value.all.return_value = []
    db.execute.side_effect = [mock_run_res, mock_sub_res, mock_run_res, mock_sub_res]

    await WorkflowService.fork_workflow_run(
        db=db,
        workflow_run_id=source_run.id,
        from_step_order=2,
    )

    added_steps = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], WorkflowStep)]
    assert len(added_steps) == 2  # Only steps 1 and 2 cloned
    assert added_steps[0].step_order == 1
    assert added_steps[0].status == "success"
    assert added_steps[1].step_order == 2
    assert added_steps[1].status == "queued"


def test_schema_validations_for_priority_and_fork():
    """Verify schema boundary constraints on priority and fork requests."""
    # Priority boundaries (-1000 to 1000)
    wf_valid = WorkflowCreate(workflow_name="test", priority=-10)
    assert wf_valid.priority == -10

    with pytest.raises(ValidationError):
        WorkflowCreate(workflow_name="test", priority=-2000)

    with pytest.raises(ValidationError):
        WorkflowCreate(workflow_name="test", priority=2000)

    # Fork request validations
    fork_valid = WorkflowForkRequest(from_step_order=3, priority=-5)
    assert fork_valid.from_step_order == 3
    assert fork_valid.priority == -5

    with pytest.raises(ValidationError):
        WorkflowForkRequest(from_step_order=0)  # Must be >= 1
