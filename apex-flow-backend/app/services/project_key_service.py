import uuid
from datetime import datetime, timezone
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException, UnauthorizedException
from app.core.security import generate_project_key, hash_api_key

from app.models.project_key import ProjectKey
from app.schemas.project_key import ProjectKeyCreate, ProjectKeyCreatedResponse


class ProjectKeyService:
    @staticmethod
    async def create_project_key(
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: ProjectKeyCreate,
    ) -> ProjectKeyCreatedResponse:
        """
        Creates a new API project key for a user.
        Generates secret key once and stores SHA-256 hash.
        """
        raw_key, key_prefix, key_hash = generate_project_key()

        project_key = ProjectKey(
            user_id=user_id,
            name=payload.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            status="active",
        )
        db.add(project_key)
        await db.commit()
        await db.refresh(project_key)

        return ProjectKeyCreatedResponse(
            id=project_key.id,
            user_id=project_key.user_id,
            name=project_key.name,
            key_prefix=project_key.key_prefix,
            status=project_key.status,
            last_used_at=project_key.last_used_at,
            created_at=project_key.created_at,
            updated_at=project_key.updated_at,
            raw_key=raw_key,
        )

    @staticmethod
    async def authenticate_api_key(db: AsyncSession, raw_key: str) -> uuid.UUID:
        """
        Authenticates an incoming project API key header.
        Updates last_used_at timestamp and returns user_id.
        """
        hashed = hash_api_key(raw_key)
        query = select(ProjectKey).where(
            ProjectKey.key_hash == hashed,
            ProjectKey.status == "active",
        )
        result = await db.execute(query)
        key = result.scalar_one_or_none()

        if not key:
            raise UnauthorizedException("Invalid or revoked project API key.")

        key.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        return key.user_id

    @staticmethod
    async def list_project_keys(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[ProjectKey]:
        """Lists all active or revoked project keys for a given user."""
        query = (
            select(ProjectKey)
            .where(ProjectKey.user_id == user_id)
            .order_by(ProjectKey.created_at.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_project_key(
        db: AsyncSession,
        user_id: uuid.UUID,
        key_id: uuid.UUID,
    ) -> ProjectKey:
        """Permanently deletes a project key by ID."""
        query = select(ProjectKey).where(
            ProjectKey.id == key_id,
            ProjectKey.user_id == user_id,
        )
        result = await db.execute(query)
        key = result.scalar_one_or_none()

        if not key:
            raise EntityNotFoundException("ProjectKey", key_id)

        await db.delete(key)
        await db.commit()
        return key


