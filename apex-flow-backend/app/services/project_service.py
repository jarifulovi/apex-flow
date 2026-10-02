import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.project import Project
from app.schemas.project import ProjectCreate


class ProjectService:
    @staticmethod
    async def create_project(
        db: AsyncSession,
        owner_id: uuid.UUID,
        payload: ProjectCreate,
    ) -> Project:
        """Create a new project for a user."""
        project = Project(
            owner_id=owner_id,
            name=payload.name,
            metadata_=payload.metadata or {},
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        owner_id: uuid.UUID,
    ) -> List[Project]:
        """List all projects belonging to an owner."""
        query = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_or_create_default_project(
        db: AsyncSession,
        owner_id: uuid.UUID,
    ) -> Project:
        """Get or automatically create a Default Project for a user."""
        query = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.asc())
            .limit(1)
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            project = Project(
                owner_id=owner_id,
                name="Default Project",
                metadata_={"is_default": True},
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)

        return project

    @staticmethod
    async def get_project_by_id(
        db: AsyncSession,
        project_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Project:
        """Fetch project details by ID with optional owner scoping."""
        query = select(Project).where(Project.id == project_id)
        if owner_id:
            query = query.where(Project.owner_id == owner_id)

        result = await db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            raise EntityNotFoundException("Project", project_id)

        return project
