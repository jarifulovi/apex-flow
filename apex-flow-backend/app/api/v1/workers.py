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
from app.schemas.worker import WorkerHeartbeatRequest, WorkerResponse
from app.services.workers import WorkerService

router = APIRouter()


@router.post("/workers/heartbeat", response_model=WorkerResponse, status_code=status.HTTP_200_OK)
async def worker_heartbeat(
    payload: WorkerHeartbeatRequest,
    key_ctx: ProjectKeyContext = Depends(get_current_project_key_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a worker or record a active heartbeat.
    Requires X-ApexFlow-Project-Key header.
    """
    return await WorkerService.register_or_heartbeat(
        db=db, project_id=key_ctx.project_id, payload=payload
    )


@router.get("/workers", response_model=List[WorkerResponse])
async def list_workers(
    project_id: Optional[uuid.UUID] = None,
    authenticated_user_id: uuid.UUID = Depends(get_current_user_from_any_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    List connected execution workers for a project.
    """
    return await WorkerService.list_workers(
        db=db, owner_id=authenticated_user_id, project_id=project_id
    )
