import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.step import WorkflowStep
from app.models.workflow import Workflow
from app.schemas.step import StepReportPayload, StepStatus
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowStatus


@pytest.mark.asyncio
async def test_workflow_and_step_orm_models(db: AsyncSession, test_user_id: uuid.UUID):
    """Test creating and querying Workflow and WorkflowStep ORM records in the database"""
    # Create workflow referencing valid test_user_id
    workflow = Workflow(
        user_id=test_user_id,
        status="pending",
        metadata_={"environment": "test"},
    )
    db.add(workflow)
    await db.flush()

    assert workflow.id is not None
    assert workflow.status == "pending"
    assert workflow.metadata_ == {"environment": "test"}

    # Create step
    step = WorkflowStep(
        workflow_id=workflow.id,
        step_name="extract-data",
        status="queued",
        input_payload={"user_input": "hello"},
    )
    db.add(step)
    await db.flush()

    assert step.id is not None
    assert step.workflow_id == workflow.id
    assert step.step_name == "extract-data"
    assert step.status == "queued"

    # Query relationship
    stmt = select(Workflow).where(Workflow.id == workflow.id)
    res = await db.execute(stmt)
    fetched_wf = res.scalar_one()

    # Clean up workflow & step records
    await db.delete(fetched_wf)
    await db.commit()


def test_pydantic_schemas():
    """Test Pydantic schema serialization and validation"""
    user_id = uuid.uuid4()

    wf_create = WorkflowCreate(user_id=user_id, metadata={"tag": "ai_agent"})
    assert wf_create.user_id == user_id
    assert wf_create.metadata == {"tag": "ai_agent"}

    report = StepReportPayload(
        step_id=uuid.uuid4(),
        status=StepStatus.SUCCESS,
        output_payload={"result": "extracted_info"},
    )
    assert report.status == StepStatus.SUCCESS
    assert report.output_payload == {"result": "extracted_info"}
