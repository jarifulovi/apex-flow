import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.step import StepReportPayload, WorkflowStepCreate


class StepService:
    @staticmethod
    async def create_step(db: AsyncSession, payload: WorkflowStepCreate) -> WorkflowStep:
        """Queue a new step under an existing workflow run."""
        now = datetime.now(timezone.utc)

        # Update parent workflow status to running if pending (atomic query, non-blocking)
        await db.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == payload.workflow_id, WorkflowRun.status == "pending")
            .values(status="running", started_at=func.coalesce(WorkflowRun.started_at, now))
        )

        step = WorkflowStep(
            workflow_run_id=payload.workflow_id,
            step_name=payload.step_name,
            status="queued",
            max_attempts=payload.max_attempts,
            input_payload=payload.input_payload or {},
        )
        db.add(step)
        await db.commit()
        await db.refresh(step)
        return step

    @staticmethod
    async def report_step_status(db: AsyncSession, payload: StepReportPayload) -> WorkflowStep:
        """
        Report execution result of a step (success or failed) and update workflow run state.
        """
        now = datetime.now(timezone.utc)
        stmt = select(WorkflowStep).where(WorkflowStep.id == payload.step_id).with_for_update()
        result = await db.execute(stmt)
        step = result.scalar_one_or_none()

        if not step:
            raise EntityNotFoundException("WorkflowStep", payload.step_id)

        step.output_payload = payload.output_payload or {}
        step.error_message = payload.error_message
        step.locked_until = None

        if payload.status == "failed":
            step.status = "failed"
            step.completed_at = now
            await db.execute(
                update(WorkflowRun)
                .where(WorkflowRun.id == step.workflow_run_id)
                .values(status="failed", completed_at=now)
            )
        else:
            step.status = "success"
            step.completed_at = now

        await db.commit()
        await db.refresh(step)
        return step


    @staticmethod
    async def list_steps(
        db: AsyncSession,
        owner_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowStep]:
        """List workflow steps for specified owner/project with status filtering."""
        stmt = (
            select(WorkflowStep)
            .join(WorkflowRun, WorkflowStep.workflow_run_id == WorkflowRun.id)
            .join(WorkflowRun.project)
            .where(WorkflowRun.project.has(owner_id=owner_id))
        )
        if project_id:
            stmt = stmt.where(WorkflowRun.project_id == project_id)

        if status_filter and status_filter.lower() != "all":
            stmt = stmt.where(WorkflowStep.status == status_filter.lower())

        stmt = stmt.order_by(WorkflowStep.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())
