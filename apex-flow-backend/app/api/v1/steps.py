import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_project_key_context,
    get_current_user_from_any_auth,
)
from app.core.database import get_db
from app.schemas.project import ProjectKeyContext
from app.schemas.step import (
    StepPollRequest,
    StepReportPayload,
    WorkflowStepCreate,
    WorkflowStepResponse,
)
from app.services.steps import QueueService, StepService

router = APIRouter()


@router.get("/steps", response_model=list[WorkflowStepResponse])
async def list_steps(
    project_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_any_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    List workflow execution steps. Accepts Bearer JWT (Dashboard UI) or Project Key (Workers).
    """
    return await StepService.list_steps(
        db=db,
        owner_id=authenticated_user_id,
        project_id=project_id,
        status_filter=status,
        limit=limit,
        offset=offset,
    )


@router.post("/steps", response_model=WorkflowStepResponse, status_code=status.HTTP_201_CREATED)
async def create_step(
    payload: WorkflowStepCreate,
    key_ctx: ProjectKeyContext = Depends(get_current_project_key_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a new step under an existing workflow run.
    Requires X-ApexFlow-Project-Key header.
    """
    return await StepService.create_step(db=db, payload=payload)


@router.post("/steps/poll", response_model=Optional[WorkflowStepResponse])
async def poll_queued_step(
    response: Response,
    payload: Optional[StepPollRequest] = None,
    key_ctx: ProjectKeyContext = Depends(get_current_project_key_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Poll the next queued step using PostgreSQL FOR UPDATE SKIP LOCKED.
    Supports targeted step_names filtering, lease locking, and worker heartbeat updates.
    Requires X-ApexFlow-Project-Key header.
    """
    step = await QueueService.poll_next_step(
        db=db, project_id=key_ctx.project_id, payload=payload
    )
    if not step:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return step


@router.post("/steps/report", response_model=WorkflowStepResponse)
async def report_step_status(
    payload: StepReportPayload,
    key_ctx: ProjectKeyContext = Depends(get_current_project_key_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Report execution result of a step (success or failed) from the SDK worker.
    Handles retry limits and updates parent workflow run status.
    Requires X-ApexFlow-Project-Key header.
    """
    return await StepService.report_step_status(db=db, payload=payload)
