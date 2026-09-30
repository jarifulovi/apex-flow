from typing import Optional
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundException
from app.models.step import WorkflowStep
from app.models.workflow import Workflow
from app.schemas.step import (
    StepReportPayload,
    WorkflowStepCreate,
    WorkflowStepResponse,
)

router = APIRouter()


@router.post("/steps", response_model=WorkflowStepResponse, status_code=status.HTTP_201_CREATED)
async def create_step(
    payload: WorkflowStepCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a new step under an existing workflow.
    """
    # Verify parent workflow exists
    wf_query = select(Workflow).where(Workflow.id == payload.workflow_id)
    wf_res = await db.execute(wf_query)
    workflow = wf_res.scalar_one_or_none()

    if not workflow:
        raise EntityNotFoundException("Workflow", payload.workflow_id)

    step = WorkflowStep(
        workflow_id=payload.workflow_id,
        step_name=payload.step_name,
        status="queued",
        input_payload=payload.input_payload or {},
    )
    db.add(step)
    await db.flush()
    await db.refresh(step)

    return step


@router.post("/steps/poll", response_model=Optional[WorkflowStepResponse])
async def poll_queued_step(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Poll the next queued step using PostgreSQL row locking (FOR UPDATE SKIP LOCKED).
    Dispatches the step exclusively to the requesting worker and marks it 'running'.
    """
    stmt = (
        select(WorkflowStep)
        .where(WorkflowStep.status == "queued")
        .order_by(WorkflowStep.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(stmt)
    step = result.scalar_one_or_none()

    if not step:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    # Transition step state to running & increment attempt counter
    step.status = "running"
    step.attempt_count += 1

    # Transition parent workflow status to running if pending
    wf_stmt = select(Workflow).where(Workflow.id == step.workflow_id).with_for_update()
    wf_res = await db.execute(wf_stmt)
    parent_wf = wf_res.scalar_one_or_none()
    if parent_wf and parent_wf.status == "pending":
        parent_wf.status = "running"

    await db.commit()
    await db.refresh(step)

    return step


@router.post("/steps/report", response_model=WorkflowStepResponse)
async def report_step_status(
    payload: StepReportPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Report execution result of a step from the SDK worker (success or failed).
    Automatically updates parent workflow run state when all steps complete.
    """
    stmt = select(WorkflowStep).where(WorkflowStep.id == payload.step_id).with_for_update()
    result = await db.execute(stmt)
    step = result.scalar_one_or_none()

    if not step:
        raise EntityNotFoundException("WorkflowStep", payload.step_id)

    # Update step execution results
    step.status = payload.status.value
    step.output_payload = payload.output_payload or {}
    step.error_message = payload.error_message

    # Check parent workflow status
    wf_stmt = select(Workflow).where(Workflow.id == step.workflow_id).with_for_update()
    wf_res = await db.execute(wf_stmt)
    parent_wf = wf_res.scalar_one_or_none()

    if parent_wf:
        if payload.status == "failed":
            parent_wf.status = "failed"
        else:
            # Check if any steps are still queued or running for this workflow
            from sqlalchemy import func
            pending_steps_stmt = select(func.count(WorkflowStep.id)).where(
                WorkflowStep.workflow_id == parent_wf.id,
                WorkflowStep.status.in_(["queued", "running"]),
                WorkflowStep.id != step.id,
            )
            pending_count_res = await db.execute(pending_steps_stmt)
            pending_count = pending_count_res.scalar_one()

            if pending_count == 0:
                parent_wf.status = "completed"

    await db.commit()
    await db.refresh(step)

    return step
