import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_from_jwt
from app.core.database import get_db
from app.schemas.project_key import (
    ProjectKeyCreate,
    ProjectKeyCreatedResponse,
    ProjectKeyResponse,
)
from app.services.project_key_service import ProjectKeyService

router = APIRouter()


@router.post("/keys", response_model=ProjectKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_project_key(
    payload: ProjectKeyCreate,
    user_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new API project key for SDK/Worker authentication.
    The full secret key (`raw_key`) is returned ONLY ONCE in this response.
    """
    return await ProjectKeyService.create_project_key(
        db=db, user_id=user_id, payload=payload
    )


@router.get("/keys", response_model=List[ProjectKeyResponse])
async def list_project_keys(
    user_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    List all project keys belonging to the authenticated user.
    """
    return await ProjectKeyService.list_project_keys(db=db, user_id=user_id)


@router.delete("/keys/{key_id}", response_model=ProjectKeyResponse)
async def revoke_project_key(
    key_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_from_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke a project key by ID. Revoked keys cannot be used for SDK execution.
    """
    return await ProjectKeyService.revoke_project_key(
        db=db, user_id=user_id, key_id=key_id
    )
