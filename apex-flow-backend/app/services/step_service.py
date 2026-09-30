import uuid
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.step import WorkflowStep
from app.models.workflow import Workflow
from app.schemas.step import StepReportPayload, WorkflowStepCreate


class StepService:
    @staticmethod
    async def create_step(db: AsyncSession, payload: WorkflowStepCreate) -> WorkflowStep:
        """Queue a new step under an existing workflow."""
        # Verify parent workflow exists
        wf_query = select(Workflow).where(Workflow.id == payload.workflow_id)
        wf_res = await db.execute(wf_query)
        workflow = wf_res.scalar_one_or_none()

        if not workflow:
            raise EntityNotFoundException("Workflow", payload.workflow_id)

        step = WorkflowStep(
            workflow_id=payload.workflow_id,
            step_name=payload.step_name,
            status="queued",
            input_payload=payload.input_payload or {},
        )
        db.add(step)
        await db.flush()
        await db.refresh(step)
        return step

    @staticmethod
    async def poll_next_step(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[WorkflowStep]:
        """
        Poll the next queued step using PostgreSQL FOR UPDATE SKIP LOCKED.
        Transitions step status to 'running' and increments attempt counter.
        Supports multi-tenant user_id scoping.
        """
        stmt = (
            select(WorkflowStep)
            .join(Workflow, WorkflowStep.workflow_id == Workflow.id)
            .where(WorkflowStep.status == "queued")
        )
        if user_id:
            stmt = stmt.where(Workflow.user_id == user_id)

        stmt = (
            stmt.order_by(WorkflowStep.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(stmt)
        step = result.scalar_one_or_none()


        if not step:
            return None

        # Transition step state to running & increment attempt counter
        step.status = "running"
        step.attempt_count += 1

        # Transition parent workflow status to running if pending
        wf_stmt = select(Workflow).where(Workflow.id == step.workflow_id).with_for_update()
        wf_res = await db.execute(wf_stmt)
        parent_wf = wf_res.scalar_one_or_none()
        if parent_wf and parent_wf.status == "pending":
            parent_wf.status = "running"

        await db.commit()
        await db.refresh(step)
        return step

    @staticmethod
    async def report_step_status(db: AsyncSession, payload: StepReportPayload) -> WorkflowStep:
        """
        Report execution result of a step (success or failed) and update workflow state.
        """
        stmt = select(WorkflowStep).where(WorkflowStep.id == payload.step_id).with_for_update()
        result = await db.execute(stmt)
        step = result.scalar_one_or_none()

        if not step:
            raise EntityNotFoundException("WorkflowStep", payload.step_id)

        # Update step execution results
        step.status = payload.status.value
        step.output_payload = payload.output_payload or {}
        step.error_message = payload.error_message

        # Evaluate parent workflow state
        wf_stmt = select(Workflow).where(Workflow.id == step.workflow_id).with_for_update()
        wf_res = await db.execute(wf_stmt)
        parent_wf = wf_res.scalar_one_or_none()

        if parent_wf:
            if payload.status == "failed":
                parent_wf.status = "failed"
            else:
                # Check if any steps are still queued or running for this workflow
                pending_steps_stmt = select(func.count(WorkflowStep.id)).where(
                    WorkflowStep.workflow_id == parent_wf.id,
                    WorkflowStep.status.in_(["queued", "running"]),
                    WorkflowStep.id != step.id,
                )
                pending_count_res = await db.execute(pending_steps_stmt)
                pending_count = pending_count_res.scalar_one()

                if pending_count == 0:
                    parent_wf.status = "completed"

        await db.commit()
        await db.refresh(step)
        return step
