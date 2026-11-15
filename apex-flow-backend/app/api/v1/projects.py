import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_from_jwt
from app.core.database import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectMetricsResponse,
    ProjectOverviewResponse,
    ProjectPurgeResponse,
    ProjectResponse,
    ProjectUpdate,
    WebhookTestRequest,
    WebhookTestResponse,
)
from app.services.alerts import AlertService
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


@router.get("/projects/{project_id}/overview", response_model=ProjectOverviewResponse)
async def get_project_overview(
    project_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Fetch consolidated project telemetry, metrics, and recent activity in 1 single HTTP request."""
    return await ProjectService.get_project_overview(db=db, project_id=project_id, owner_id=owner_id)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Update project name and alert webhook settings."""
    try:
        return await ProjectService.update_project(
            db=db, project_id=project_id, owner_id=owner_id, payload=payload
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post("/projects/{project_id}/purge", response_model=ProjectPurgeResponse)
async def purge_project_logs(
    project_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Purge finished workflow execution runs and steps for a project."""
    deleted_count = await ProjectService.purge_project_logs(
        db=db, project_id=project_id, owner_id=owner_id
    )
    return ProjectPurgeResponse(deleted_runs=deleted_count)


@router.post("/projects/{project_id}/alerts/test", response_model=WebhookTestResponse)
async def test_project_alert_webhook(
    project_id: uuid.UUID,
    payload: Optional[WebhookTestRequest] = None,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Dispatch a real verification webhook message to test project Slack/Discord/HTTP alerting."""
    project = await ProjectService.get_project_by_id(
        db=db, project_id=project_id, owner_id=owner_id
    )
    try:
        return await AlertService.send_test_alert(
            project=project,
            override_url=payload.webhook_url if payload else None,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project by ID, preventing deletion of Default Project."""
    try:
        await ProjectService.delete_project(db=db, project_id=project_id, owner_id=owner_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


