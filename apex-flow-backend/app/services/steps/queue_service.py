import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select, update
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
        )
        if db.bind and db.bind.dialect.name == "postgresql":
            stale_query = stale_query.with_for_update(of=WorkflowStep, skip_locked=True)

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
                await db.execute(
                    update(WorkflowRun)
                    .where(WorkflowRun.id == step.workflow_run_id)
                    .values(status="failed", completed_at=now)
                )

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

        stmt = stmt.order_by(WorkflowStep.created_at.asc()).limit(1)
        if db.bind and db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(of=WorkflowStep, skip_locked=True)

        result = await db.execute(stmt)
        step = result.scalar_one_or_none()

        if not step:
            return None

        # 4. Acquire step atomically: transition to running only if still 'queued'
        lock_duration = timedelta(seconds=poll_payload.lock_duration_seconds)
        locked_until_time = now + lock_duration

        acquire_stmt = (
            update(WorkflowStep)
            .where(WorkflowStep.id == step.id, WorkflowStep.status == "queued")
            .values(
                status="running",
                attempt_count=step.attempt_count + 1,
                started_at=func.coalesce(WorkflowStep.started_at, now),
                locked_until=locked_until_time,
            )
        )
        acquire_res = await db.execute(acquire_stmt)
        if acquire_res.rowcount == 0:
            # Step was acquired by a concurrent worker between SELECT and UPDATE
            await db.rollback()
            return None

        # 5. Update parent workflow run state to running if pending (non-blocking atomic update)
        await db.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == step.workflow_run_id, WorkflowRun.status == "pending")
            .values(status="running", started_at=func.coalesce(WorkflowRun.started_at, now))
        )

        await db.commit()
        await db.refresh(step)
        return step
