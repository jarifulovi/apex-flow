import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_from_api_key
from app.core.database import get_db
from app.schemas.step import (
    StepReportPayload,
    WorkflowStepCreate,
    WorkflowStepResponse,
)
from app.services.step_service import StepService

router = APIRouter()


@router.post("/steps", response_model=WorkflowStepResponse, status_code=status.HTTP_201_CREATED)
async def create_step(
    payload: WorkflowStepCreate,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a new step under an existing workflow.
    Requires X-ApexFlow-Project-Key header.
    """
    return await StepService.create_step(db=db, payload=payload)


@router.post("/steps/poll", response_model=Optional[WorkflowStepResponse])
async def poll_queued_step(
    response: Response,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Poll the next queued step using PostgreSQL row locking (FOR UPDATE SKIP LOCKED).
    Dispatches the step exclusively to the requesting worker and marks it 'running'.
    Requires X-ApexFlow-Project-Key header.
    """
    step = await StepService.poll_next_step(db=db, user_id=authenticated_user_id)
    if not step:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return step


@router.post("/steps/report", response_model=WorkflowStepResponse)
async def report_step_status(
    payload: StepReportPayload,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Report execution result of a step from the SDK worker (success or failed).
    Automatically updates parent workflow run state when all steps complete.
    Requires X-ApexFlow-Project-Key header.
    """
    return await StepService.report_step_status(db=db, payload=payload)

