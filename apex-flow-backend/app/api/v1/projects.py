import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_from_jwt
from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectMetricsResponse, ProjectResponse
from app.services.projects import ProjectService

router = APIRouter()


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """List all projects owned by the authenticated user."""
    return await ProjectService.list_projects(db=db, owner_id=owner_id)


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project for the authenticated user."""
    return await ProjectService.create_project(db=db, owner_id=owner_id, payload=payload)


@router.get("/projects/default", response_model=ProjectResponse)
async def get_default_project(
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Fetch or auto-create the default project for the user."""
    return await ProjectService.get_or_create_default_project(db=db, owner_id=owner_id)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific project."""
    return await ProjectService.get_project_by_id(db=db, project_id=project_id, owner_id=owner_id)


@router.get("/projects/{project_id}/metrics", response_model=ProjectMetricsResponse)
async def get_project_metrics(
    project_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Fetch live project telemetry metrics summary."""
    return await ProjectService.get_project_metrics(db=db, project_id=project_id, owner_id=owner_id)
