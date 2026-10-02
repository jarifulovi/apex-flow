import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundException, UnauthorizedException
from app.core.security import generate_project_key, hash_api_key
from app.models.project_key import ProjectKey
from app.schemas.project import ProjectKeyContext
from app.schemas.project_key import ProjectKeyCreate, ProjectKeyCreatedResponse
from app.services.projects.project_service import ProjectService


class ProjectKeyService:
    @staticmethod
    async def create_project_key(
        db: AsyncSession,
        owner_id: uuid.UUID,
        payload: ProjectKeyCreate,
    ) -> ProjectKeyCreatedResponse:
        """
        Creates a new API project key for a project.
        Generates secret key once and stores SHA-256 hash.
        """
        # Resolve target project_id
        if payload.project_id:
            project = await ProjectService.get_project_by_id(
                db=db, project_id=payload.project_id, owner_id=owner_id
            )
            target_project_id = project.id
        else:
            default_project = await ProjectService.get_or_create_default_project(
                db=db, owner_id=owner_id
            )
            target_project_id = default_project.id

        raw_key, key_prefix, key_hash = generate_project_key()

        project_key = ProjectKey(
            project_id=target_project_id,
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
            project_id=project_key.project_id,
            name=project_key.name,
            key_prefix=project_key.key_prefix,
            status=project_key.status,
            last_used_at=project_key.last_used_at,
            created_at=project_key.created_at,
            updated_at=project_key.updated_at,
            raw_key=raw_key,
        )

    @staticmethod
    async def authenticate_api_key(
        db: AsyncSession, raw_key: str
    ) -> ProjectKeyContext:
        """
        Authenticates an incoming project API key header.
        Updates last_used_at timestamp and returns ProjectKeyContext.
        """
        hashed = hash_api_key(raw_key)
        query = (
            select(ProjectKey)
            .options(selectinload(ProjectKey.project))
            .where(
                ProjectKey.key_hash == hashed,
                ProjectKey.status == "active",
            )
        )
        result = await db.execute(query)
        key = result.scalar_one_or_none()

        if not key or not key.project:
            raise UnauthorizedException("Invalid or revoked project API key.")

        key.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        return ProjectKeyContext(
            project_id=key.project_id,
            owner_id=key.project.owner_id,
            key_id=key.id,
        )

    @staticmethod
    async def list_project_keys(
        db: AsyncSession,
        owner_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> List[ProjectKey]:
        """Lists active/revoked project keys for a given owner or project."""
        query = (
            select(ProjectKey)
            .join(ProjectKey.project)
            .where(ProjectKey.project.has(owner_id=owner_id))
        )
        if project_id:
            query = query.where(ProjectKey.project_id == project_id)

        query = query.order_by(ProjectKey.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_project_key(
        db: AsyncSession,
        owner_id: uuid.UUID,
        key_id: uuid.UUID,
    ) -> ProjectKey:
        """Permanently deletes a project key by ID."""
        query = (
            select(ProjectKey)
            .join(ProjectKey.project)
            .where(
                ProjectKey.id == key_id,
                ProjectKey.project.has(owner_id=owner_id),
            )
        )
        result = await db.execute(query)
        key = result.scalar_one_or_none()

        if not key:
            raise EntityNotFoundException("ProjectKey", key_id)

        await db.delete(key)
        await db.commit()
        return key
