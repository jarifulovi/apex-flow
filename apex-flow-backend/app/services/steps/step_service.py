import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from sqlalchemy import String, cast, func, or_, select, update
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
            step_order=payload.step_order,
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

        if payload.attempt_count is not None:
            step.attempt_count = payload.attempt_count
        elif step.attempt_count == 0:
            step.attempt_count = 1

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

            # Check if all steps under this workflow run are completed successfully
            stmt_steps = select(WorkflowStep).where(WorkflowStep.workflow_run_id == step.workflow_run_id)
            all_steps_res = await db.execute(stmt_steps)
            all_steps = list(all_steps_res.scalars().all())

            if all_steps and all(s.id == step.id or s.status == "success" for s in all_steps):
                await db.execute(
                    update(WorkflowRun)
                    .where(WorkflowRun.id == step.workflow_run_id)
                    .values(status="completed", completed_at=now)
                )

        await db.commit()
        await db.refresh(step)
        return step


    @staticmethod
    async def list_steps(
        db: AsyncSession,
        owner_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[list[WorkflowStep], int]:
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

        if search:
            pattern = f"%{search.lower().strip()}%"
            stmt = stmt.where(
                or_(
                    func.lower(WorkflowStep.step_name).like(pattern),
                    func.lower(cast(WorkflowStep.id, String)).like(pattern),
                    func.lower(cast(WorkflowStep.workflow_run_id, String)).like(pattern),
                )
            )

        # Count total items matching filter
        subq = stmt.subquery()
        count_stmt = select(func.count()).select_from(subq)
        total_count_res = await db.execute(count_stmt)
        total_count = total_count_res.scalar() or 0

        # Fetch items
        items_stmt = stmt.order_by(WorkflowStep.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(items_stmt)
        items = list(result.scalars().all())
        return items, total_count

    @staticmethod
    async def get_step_status_counts(
        db: AsyncSession,
        owner_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, int]:
        """Get step count per status for filter tabs."""
        stmt = (
            select(WorkflowStep.status, func.count(WorkflowStep.id))
            .join(WorkflowRun, WorkflowStep.workflow_run_id == WorkflowRun.id)
            .join(WorkflowRun.project)
            .where(WorkflowRun.project.has(owner_id=owner_id))
            .group_by(WorkflowStep.status)
        )
        if project_id:
            stmt = stmt.where(WorkflowRun.project_id == project_id)

        result = await db.execute(stmt)
        counts: Dict[str, int] = {"all": 0, "queued": 0, "running": 0, "success": 0, "failed": 0, "cancelled": 0}
        total = 0
        for status_val, count_val in result.all():
            if status_val in counts:
                counts[status_val] = count_val
            total += count_val
        counts["all"] = total
        return counts
