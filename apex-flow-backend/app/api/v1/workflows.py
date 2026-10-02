import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_project_key_context,
    get_current_user_from_any_auth,
)
from app.core.database import get_db
from app.schemas.project import ProjectKeyContext
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
    key_ctx: ProjectKeyContext = Depends(get_current_project_key_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workflow run execution state.
    Requires X-ApexFlow-Project-Key header.
    """
    return await WorkflowService.create_workflow_run(
        db=db, payload=payload, project_id=key_ctx.project_id
    )


@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows(
    project_id: Optional[uuid.UUID] = None,
    workflow_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_any_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    List workflow execution runs. Accepts Bearer JWT (Dashboard UI) or Project Key (Workers).
    """
    return await WorkflowService.list_workflow_runs(
        db=db,
        owner_id=authenticated_user_id,
        project_id=project_id,
        workflow_name=workflow_name,
        limit=limit,
        offset=offset,
    )


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow_detail(
    workflow_id: uuid.UUID,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_any_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed workflow run by ID, including all step execution timelines.
    Enforces multi-tenant isolation.
    """
    return await WorkflowService.get_workflow_run_by_id(
        db=db, workflow_run_id=workflow_id, owner_id=authenticated_user_id
    )
