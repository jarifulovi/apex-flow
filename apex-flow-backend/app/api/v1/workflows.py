import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundException
from app.models.workflow import Workflow
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowDetailResponse,
    WorkflowResponse,
)

router = APIRouter()


@router.post("/workflows", response_model=WorkflowDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workflow run execution state.
    """
    workflow = Workflow(
        user_id=payload.user_id,
        status="pending",
        metadata_=payload.metadata or {},
    )
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow, ["steps"])

    return workflow


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
    query = select(Workflow).order_by(Workflow.created_at.desc()).offset(offset).limit(limit)
    if user_id:
        query = query.where(Workflow.user_id == user_id)

    result = await db.execute(query)
    workflows = result.scalars().all()
    return workflows


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow_detail(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed workflow run by ID, including all step execution timelines.
    """
    query = (
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(selectinload(Workflow.steps))
    )
    result = await db.execute(query)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise EntityNotFoundException("Workflow", workflow_id)

    return workflow
