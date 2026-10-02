import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundException
from app.models.workflow_run import WorkflowRun
from app.schemas.workflow import WorkflowCreate
from app.services.projects.project_service import ProjectService


class WorkflowService:
    @staticmethod
    async def create_workflow_run(
        db: AsyncSession,
        payload: WorkflowCreate,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> WorkflowRun:
        """Create a new master workflow run under a project."""
        target_project_id = project_id or payload.project_id

        if not target_project_id:
            if not owner_id:
                raise ValueError("Either project_id or owner_id must be provided to create a workflow run.")
            default_project = await ProjectService.get_or_create_default_project(
                db=db, owner_id=owner_id
            )
            target_project_id = default_project.id

        workflow_run = WorkflowRun(
            project_id=target_project_id,
            workflow_name=payload.workflow_name,
            status="pending",
            metadata_=payload.metadata or {},
        )
        db.add(workflow_run)
        await db.commit()
        await db.refresh(workflow_run)
        return workflow_run

    @staticmethod
    async def list_workflow_runs(
        db: AsyncSession,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        workflow_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkflowRun]:
        """List workflow runs with optional project or owner filtering."""
        query = (
            select(WorkflowRun)
            .order_by(WorkflowRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if project_id:
            query = query.where(WorkflowRun.project_id == project_id)
        elif owner_id:
            query = query.join(WorkflowRun.project).where(WorkflowRun.project.has(owner_id=owner_id))

        if workflow_name:
            query = query.where(WorkflowRun.workflow_name == workflow_name)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_workflow_run_by_id(
        db: AsyncSession,
        workflow_run_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> WorkflowRun:
        """Fetch workflow run detail by ID with steps loaded."""
        query = (
            select(WorkflowRun)
            .where(WorkflowRun.id == workflow_run_id)
            .options(selectinload(WorkflowRun.steps))
        )

        if project_id:
            query = query.where(WorkflowRun.project_id == project_id)
        elif owner_id:
            query = query.join(WorkflowRun.project).where(WorkflowRun.project.has(owner_id=owner_id))

        result = await db.execute(query)
        workflow_run = result.scalar_one_or_none()

        if not workflow_run:
            raise EntityNotFoundException("WorkflowRun", workflow_run_id)

        return workflow_run
