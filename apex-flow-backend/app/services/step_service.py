import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.step import StepPollRequest, StepReportPayload, WorkflowStepCreate
from app.schemas.worker import WorkerHeartbeatRequest
from app.services.worker_service import WorkerService


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
    async def recover_stale_locks(db: AsyncSession, project_id: uuid.UUID) -> int:
        """
        Auto-re-queues steps stuck in 'running' state past their locked_until timestamp.
        If max_attempts exceeded, marks step and workflow run as 'failed'.
        """
        now = datetime.now(timezone.utc)
        
        stale_query = (
            select(WorkflowStep)
            .join(WorkflowRun, WorkflowStep.workflow_run_id == WorkflowRun.id)
            .where(
                WorkflowRun.project_id == project_id,
                WorkflowStep.status == "running",
                WorkflowStep.locked_until.is_not(None),
                WorkflowStep.locked_until < now,
            )
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(stale_query)
        stale_steps = list(result.scalars().all())

        for step in stale_steps:
            if step.attempt_count < step.max_attempts:
                step.status = "queued"
                step.locked_until = None
            else:
                step.status = "failed"
                step.error_message = "Execution lock expired (worker timeout/crash)."
                step.completed_at = now
                step.locked_until = None
                
                # Mark parent workflow run failed
                wf_res = await db.execute(
                    select(WorkflowRun).where(WorkflowRun.id == step.workflow_run_id)
                )
                parent_wf = wf_res.scalar_one_or_none()
                if parent_wf and parent_wf.status != "failed":
                    parent_wf.status = "failed"
                    parent_wf.completed_at = now

        if stale_steps:
            await db.commit()

        return len(stale_steps)

    @staticmethod
    async def poll_next_step(
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: Optional[StepPollRequest] = None,
    ) -> Optional[WorkflowStep]:
        """
        Poll the next queued step using PostgreSQL FOR UPDATE SKIP LOCKED.
        Supports targeted step_names filtering, lease locking, and worker heartbeat updating.
        """
        now = datetime.now(timezone.utc)

        # 1. Recover any expired step locks for this project first
        await StepService.recover_stale_locks(db=db, project_id=project_id)

        # 2. Register worker heartbeat if worker info provided
        poll_payload = payload or StepPollRequest()
        if poll_payload.worker_name or poll_payload.worker_id:
            await WorkerService.register_or_heartbeat(
                db=db,
                project_id=project_id,
                payload=WorkerHeartbeatRequest(
                    name=poll_payload.worker_name or "python-worker",
                    worker_id=poll_payload.worker_id,
                ),
            )

        # 3. Query next available queued step
        stmt = (
            select(WorkflowStep)
            .join(WorkflowRun, WorkflowStep.workflow_run_id == WorkflowRun.id)
            .where(
                WorkflowRun.project_id == project_id,
                WorkflowStep.status == "queued",
            )
        )

        if poll_payload.step_names:
            stmt = stmt.where(WorkflowStep.step_name.in_(poll_payload.step_names))

        stmt = (
            stmt.order_by(WorkflowStep.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(stmt)
        step = result.scalar_one_or_none()

        if not step:
            return None

        # 4. Acquire step: transition to running, set started_at and locked_until lease lock
        lock_duration = timedelta(seconds=poll_payload.lock_duration_seconds)
        step.status = "running"
        step.attempt_count += 1
        step.started_at = step.started_at or now
        step.locked_until = now + lock_duration

        # 5. Update parent workflow run state to running if pending
        wf_res = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == step.workflow_run_id).with_for_update()
        )
        parent_wf = wf_res.scalar_one_or_none()
        if parent_wf and parent_wf.status == "pending":
            parent_wf.status = "running"
            parent_wf.started_at = parent_wf.started_at or now

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
