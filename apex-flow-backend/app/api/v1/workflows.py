import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowDetailResponse,
    WorkflowResponse,
)
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("/workflows", response_model=WorkflowDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workflow run execution state.
    """
    return await WorkflowService.create_workflow(db=db, payload=payload)


@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows(
    user_id: uuid.UUID = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List workflow execution runs. Option to filter by user_id.
    """
    return await WorkflowService.list_workflows(
        db=db, user_id=user_id, limit=limit, offset=offset
    )


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow_detail(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed workflow run by ID, including all step execution timelines.
    """
    return await WorkflowService.get_workflow_by_id(db=db, workflow_id=workflow_id)
