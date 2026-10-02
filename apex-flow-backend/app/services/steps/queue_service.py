import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.step import StepPollRequest
from app.schemas.worker import WorkerHeartbeatRequest
from app.services.workers.worker_service import WorkerService


class QueueService:
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
        await QueueService.recover_stale_locks(db=db, project_id=project_id)

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
