import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.step import StepReportPayload, WorkflowStepCreate


class StepService:
    @staticmethod
    async def create_step(db: AsyncSession, payload: WorkflowStepCreate) -> WorkflowStep:
        """Queue a new step under an existing workflow run."""
        wf_query = select(WorkflowRun).where(WorkflowRun.id == payload.workflow_id)
        wf_res = await db.execute(wf_query)
        workflow_run = wf_res.scalar_one_or_none()

        if not workflow_run:
            raise EntityNotFoundException("WorkflowRun", payload.workflow_id)

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
        Handles retry logic when attempt_count < max_attempts.
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

        wf_stmt = select(WorkflowRun).where(WorkflowRun.id == step.workflow_run_id).with_for_update()
        wf_res = await db.execute(wf_stmt)
        parent_wf = wf_res.scalar_one_or_none()

        if payload.status == "failed":
            if step.attempt_count < step.max_attempts:
                # Re-queue for retry attempt
                step.status = "queued"
            else:
                # Permanent failure
                step.status = "failed"
                step.completed_at = now
                if parent_wf:
                    parent_wf.status = "failed"
                    parent_wf.completed_at = now
        else:
            # Step succeeded
            step.status = "success"
            step.completed_at = now

            if parent_wf:
                # Check if all steps for this workflow run are finished
                pending_count_res = await db.execute(
                    select(func.count(WorkflowStep.id)).where(
                        WorkflowStep.workflow_run_id == parent_wf.id,
                        WorkflowStep.status.in_(["queued", "running"]),
                        WorkflowStep.id != step.id,
                    )
                )
                pending_count = pending_count_res.scalar_one()

                if pending_count == 0:
                    parent_wf.status = "completed"
                    parent_wf.completed_at = now

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
