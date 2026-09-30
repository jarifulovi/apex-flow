import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundException
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate


class WorkflowService:
    @staticmethod
    async def create_workflow(db: AsyncSession, payload: WorkflowCreate) -> Workflow:
        """Create a new workflow execution run."""
        workflow = Workflow(
            user_id=payload.user_id,
            status="pending",
            metadata_=payload.metadata or {},
        )
        db.add(workflow)
        await db.flush()
        await db.refresh(workflow, ["steps"])
        return workflow

    @staticmethod
    async def list_workflows(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Workflow]:
        """List workflow runs with optional user filtering."""
        query = select(Workflow).order_by(Workflow.created_at.desc()).offset(offset).limit(limit)
        if user_id:
            query = query.where(Workflow.user_id == user_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_workflow_by_id(db: AsyncSession, workflow_id: uuid.UUID) -> Workflow:
        """Get workflow detail by ID or raise EntityNotFoundException."""
        query = (
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.steps))
        )
        result = await db.execute(query)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise EntityNotFoundException("Workflow", workflow_id)

        return workflow
