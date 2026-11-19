from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_project_key_context,
    get_current_user_from_headers,
)
from app.core.database import get_db
from app.schemas.project import ProjectKeyContext
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleSyncRequest,
    ScheduleTriggerResponse,
    ScheduleUpdate,
)
from app.services.projects import ProjectService
from app.services.schedules import ScheduleService

router = APIRouter()


async def _ensure_project_access(
    db: AsyncSession,
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    """Verify the authenticated user or project key owner has access to project_id."""
    await ProjectService.get_project_by_id(
        db=db,
        project_id=project_id,
        owner_id=owner_id,
    )


@router.get(
    "/projects/{project_id}/schedules",
    response_model=List[ScheduleResponse],
)
async def list_project_schedules(
    project_id: uuid.UUID,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """List all workflow schedules configured for a project."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    return await ScheduleService.list_schedules(db=db, project_id=project_id)


@router.post(
    "/projects/{project_id}/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_schedule(
    project_id: uuid.UUID,
    payload: ScheduleCreate,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Create a recurring cron schedule for a workflow in a project."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    try:
        return await ScheduleService.create_schedule(
            db=db,
            project_id=project_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/projects/{project_id}/schedules/{schedule_id}",
    response_model=ScheduleResponse,
)
async def get_project_schedule(
    project_id: uuid.UUID,
    schedule_id: uuid.UUID,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single workflow schedule by ID."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    return await ScheduleService.get_schedule_by_id(
        db=db,
        project_id=project_id,
        schedule_id=schedule_id,
    )


@router.patch(
    "/projects/{project_id}/schedules/{schedule_id}",
    response_model=ScheduleResponse,
)
async def update_project_schedule(
    project_id: uuid.UUID,
    schedule_id: uuid.UUID,
    payload: ScheduleUpdate,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Update cron expression, timezone, workflow name, or active state for a schedule."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    try:
        return await ScheduleService.update_schedule(
            db=db,
            project_id=project_id,
            schedule_id=schedule_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/projects/{project_id}/schedules/{schedule_id}/pause",
    response_model=ScheduleResponse,
)
async def pause_project_schedule(
    project_id: uuid.UUID,
    schedule_id: uuid.UUID,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active workflow schedule."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    return await ScheduleService.pause_schedule(
        db=db,
        project_id=project_id,
        schedule_id=schedule_id,
    )


@router.post(
    "/projects/{project_id}/schedules/{schedule_id}/resume",
    response_model=ScheduleResponse,
)
async def resume_project_schedule(
    project_id: uuid.UUID,
    schedule_id: uuid.UUID,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused workflow schedule and recompute next_run_at."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    return await ScheduleService.resume_schedule(
        db=db,
        project_id=project_id,
        schedule_id=schedule_id,
    )


@router.delete(
    "/projects/{project_id}/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_schedule(
    project_id: uuid.UUID,
    schedule_id: uuid.UUID,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Delete a workflow schedule permanently."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    await ScheduleService.delete_schedule(
        db=db,
        project_id=project_id,
        schedule_id=schedule_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/schedules/{schedule_id}/run",
    response_model=ScheduleTriggerResponse,
)
async def trigger_project_schedule_now(
    project_id: uuid.UUID,
    schedule_id: uuid.UUID,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a workflow execution run immediately from a schedule."""
    await _ensure_project_access(db=db, project_id=project_id, owner_id=authenticated_user_id)
    schedule, workflow_run = await ScheduleService.trigger_run_now(
        db=db,
        project_id=project_id,
        schedule_id=schedule_id,
    )
    return ScheduleTriggerResponse(schedule=schedule, workflow_run_id=workflow_run.id)


@router.post(
    "/schedules/sync",
    response_model=List[ScheduleResponse],
)
async def sync_worker_schedules(
    payload: ScheduleSyncRequest,
    key_ctx: ProjectKeyContext = Depends(get_current_project_key_context),
    db: AsyncSession = Depends(get_db),
):
    """Idempotently register or update cron schedules declared by a worker on startup."""
    return await ScheduleService.sync_worker_schedules(
        db=db,
        project_id=key_ctx.project_id,
        declarations=payload.schedules,
    )

