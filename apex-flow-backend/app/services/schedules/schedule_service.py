from datetime import datetime, timezone
import logging
from typing import List, Optional, Set, Tuple
import uuid
from zoneinfo import ZoneInfo
from croniter import croniter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.schedule import WorkflowSchedule
from app.models.step import WorkflowStep
from app.models.workflow_run import WorkflowRun
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    WorkerScheduleDeclaration,
    validate_cron_expression,
    validate_timezone_name,
)
from app.services.steps.notifier import QueueNotifier

logger = logging.getLogger(__name__)


class ScheduleService:
    """Manages recurring cron schedules, dispatch ticking, and worker startup sync."""

    @staticmethod
    def calculate_next_run(
        cron_expression: str,
        tz_name: str = "UTC",
        base_time: Optional[datetime] = None,
    ) -> datetime:
        """Compute the next timezone-aware UTC trigger timestamp from a 5-field cron."""
        validated_cron = validate_cron_expression(cron_expression)
        validated_tz = validate_timezone_name(tz_name)
        tz = ZoneInfo(validated_tz)

        ref_utc = base_time if base_time is not None else datetime.now(timezone.utc)
        if ref_utc.tzinfo is None:
            ref_utc = ref_utc.replace(tzinfo=timezone.utc)
        else:
            ref_utc = ref_utc.astimezone(timezone.utc)

        local_base = ref_utc.astimezone(tz)
        next_local = croniter(validated_cron, local_base).get_next(datetime)
        if next_local.tzinfo is None:
            next_local = next_local.replace(tzinfo=tz)
        return next_local.astimezone(timezone.utc)

    @staticmethod
    async def _dispatch_schedule_execution(
        db: AsyncSession,
        schedule: WorkflowSchedule,
        trigger_source: str,
        now: datetime,
    ) -> WorkflowRun:
        """Create a WorkflowRun and an entrypoint dispatch WorkflowStep for a schedule."""
        workflow_run = WorkflowRun(
            id=uuid.uuid4(),
            project_id=schedule.project_id,
            workflow_name=schedule.workflow_name,
            status="pending",
            metadata_={
                "trigger_source": trigger_source,
                "schedule_id": str(schedule.id),
                "cron_expression": schedule.cron_expression,
                "timezone": schedule.timezone,
            },
            priority=0,
        )
        db.add(workflow_run)
        await db.flush()

        dispatch_step = WorkflowStep(
            workflow_run_id=workflow_run.id,
            step_name=schedule.workflow_name,
            step_order=0,
            status="queued",
            max_attempts=3,
            priority=0,
            available_at=now,
            input_payload={
                "trigger_source": trigger_source,
                "schedule_id": str(schedule.id),
                "workflow_name": schedule.workflow_name,
            },
        )
        db.add(dispatch_step)
        return workflow_run

    @staticmethod
    async def dispatch_due_schedules(
        db: AsyncSession,
        project_id: Optional[uuid.UUID] = None,
        now_override: Optional[datetime] = None,
    ) -> int:
        """
        Claim due active schedules using row-level locking, trigger workflow runs,
        advance next_run_at, and wake long-polling workers via QueueNotifier.
        """
        now = now_override if now_override is not None else datetime.now(timezone.utc)
        stmt = (
            select(WorkflowSchedule)
            .where(
                WorkflowSchedule.is_active.is_(True),
                WorkflowSchedule.next_run_at.is_not(None),
                WorkflowSchedule.next_run_at <= now,
            )
            .order_by(WorkflowSchedule.next_run_at.asc())
        )
        if project_id is not None:
            stmt = stmt.where(WorkflowSchedule.project_id == project_id)

        if db.bind and db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        result = await db.execute(stmt)
        due_schedules = list(result.scalars().all())
        if not due_schedules:
            return 0

        notified_projects: Set[uuid.UUID] = set()
        for schedule in due_schedules:
            await ScheduleService._dispatch_schedule_execution(
                db=db,
                schedule=schedule,
                trigger_source="schedule",
                now=now,
            )
            schedule.last_run_at = now
            schedule.next_run_at = ScheduleService.calculate_next_run(
                schedule.cron_expression,
                schedule.timezone,
                base_time=now,
            )
            schedule.updated_at = now
            notified_projects.add(schedule.project_id)

        await db.commit()
        for proj_id in notified_projects:
            QueueNotifier.notify(proj_id)

        return len(due_schedules)

    @staticmethod
    async def list_schedules(
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[WorkflowSchedule]:
        """List all workflow schedules scoped to a project."""
        stmt = (
            select(WorkflowSchedule)
            .where(WorkflowSchedule.project_id == project_id)
            .order_by(WorkflowSchedule.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_schedule_by_id(
        db: AsyncSession,
        project_id: uuid.UUID,
        schedule_id: uuid.UUID,
    ) -> WorkflowSchedule:
        """Retrieve a schedule belonging to a project or raise EntityNotFoundException."""
        stmt = select(WorkflowSchedule).where(
            WorkflowSchedule.id == schedule_id,
            WorkflowSchedule.project_id == project_id,
        )
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()
        if schedule is None:
            raise EntityNotFoundException("WorkflowSchedule", schedule_id)
        return schedule

    @staticmethod
    async def create_schedule(
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ScheduleCreate,
    ) -> WorkflowSchedule:
        """Create a new workflow schedule for a project."""
        existing_res = await db.execute(
            select(WorkflowSchedule).where(
                WorkflowSchedule.project_id == project_id,
                WorkflowSchedule.workflow_name == payload.workflow_name,
            )
        )
        if existing_res.scalar_one_or_none() is not None:
            raise ValueError(
                f"A schedule for workflow '{payload.workflow_name}' already exists in this project."
            )

        next_run = (
            ScheduleService.calculate_next_run(payload.cron_expression, payload.timezone)
            if payload.is_active
            else None
        )
        schedule = WorkflowSchedule(
            project_id=project_id,
            workflow_name=payload.workflow_name,
            cron_expression=payload.cron_expression,
            timezone=payload.timezone,
            is_active=payload.is_active,
            next_run_at=next_run,
        )
        db.add(schedule)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(
                f"A schedule for workflow '{payload.workflow_name}' already exists in this project."
            ) from exc

        await db.refresh(schedule)
        return schedule

    @staticmethod
    async def update_schedule(
        db: AsyncSession,
        project_id: uuid.UUID,
        schedule_id: uuid.UUID,
        payload: ScheduleUpdate,
    ) -> WorkflowSchedule:
        """Update cron, timezone, workflow_name, or active state on an existing schedule."""
        schedule = await ScheduleService.get_schedule_by_id(
            db=db, project_id=project_id, schedule_id=schedule_id
        )

        recalculate_next = False
        if payload.workflow_name is not None and payload.workflow_name != schedule.workflow_name:
            conflict_res = await db.execute(
                select(WorkflowSchedule).where(
                    WorkflowSchedule.project_id == project_id,
                    WorkflowSchedule.workflow_name == payload.workflow_name,
                    WorkflowSchedule.id != schedule_id,
                )
            )
            if conflict_res.scalar_one_or_none() is not None:
                raise ValueError(
                    f"A schedule for workflow '{payload.workflow_name}' already exists in this project."
                )
            schedule.workflow_name = payload.workflow_name

        if payload.cron_expression is not None and payload.cron_expression != schedule.cron_expression:
            schedule.cron_expression = payload.cron_expression
            recalculate_next = True

        if payload.timezone is not None and payload.timezone != schedule.timezone:
            schedule.timezone = payload.timezone
            recalculate_next = True

        if payload.is_active is not None:
            if payload.is_active and not schedule.is_active:
                recalculate_next = True
            schedule.is_active = payload.is_active
            if not schedule.is_active:
                schedule.next_run_at = None

        if schedule.is_active and (recalculate_next or schedule.next_run_at is None):
            schedule.next_run_at = ScheduleService.calculate_next_run(
                schedule.cron_expression,
                schedule.timezone,
            )

        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError("Schedule update conflicted with an existing workflow schedule.") from exc

        await db.refresh(schedule)
        return schedule

    @staticmethod
    async def pause_schedule(
        db: AsyncSession,
        project_id: uuid.UUID,
        schedule_id: uuid.UUID,
    ) -> WorkflowSchedule:
        """Pause a schedule so background sweeps skip triggering it."""
        schedule = await ScheduleService.get_schedule_by_id(
            db=db, project_id=project_id, schedule_id=schedule_id
        )
        schedule.is_active = False
        schedule.next_run_at = None
        await db.commit()
        await db.refresh(schedule)
        return schedule

    @staticmethod
    async def resume_schedule(
        db: AsyncSession,
        project_id: uuid.UUID,
        schedule_id: uuid.UUID,
    ) -> WorkflowSchedule:
        """Resume a paused schedule and compute its upcoming next_run_at."""
        schedule = await ScheduleService.get_schedule_by_id(
            db=db, project_id=project_id, schedule_id=schedule_id
        )
        schedule.is_active = True
        schedule.next_run_at = ScheduleService.calculate_next_run(
            schedule.cron_expression,
            schedule.timezone,
        )
        await db.commit()
        await db.refresh(schedule)
        return schedule

    @staticmethod
    async def delete_schedule(
        db: AsyncSession,
        project_id: uuid.UUID,
        schedule_id: uuid.UUID,
    ) -> None:
        """Delete a workflow schedule permanently."""
        schedule = await ScheduleService.get_schedule_by_id(
            db=db, project_id=project_id, schedule_id=schedule_id
        )
        await db.delete(schedule)
        await db.commit()

    @staticmethod
    async def trigger_run_now(
        db: AsyncSession,
        project_id: uuid.UUID,
        schedule_id: uuid.UUID,
    ) -> Tuple[WorkflowSchedule, WorkflowRun]:
        """Trigger an immediate workflow execution from a schedule without shifting next_run_at."""
        schedule = await ScheduleService.get_schedule_by_id(
            db=db, project_id=project_id, schedule_id=schedule_id
        )
        now = datetime.now(timezone.utc)
        workflow_run = await ScheduleService._dispatch_schedule_execution(
            db=db,
            schedule=schedule,
            trigger_source="schedule_manual",
            now=now,
        )
        schedule.last_run_at = now
        schedule.updated_at = now

        await db.commit()
        await db.refresh(schedule)
        await db.refresh(workflow_run)
        QueueNotifier.notify(schedule.project_id)
        return schedule, workflow_run

    @staticmethod
    async def sync_worker_schedules(
        db: AsyncSession,
        project_id: uuid.UUID,
        declarations: List[WorkerScheduleDeclaration],
    ) -> List[WorkflowSchedule]:
        """Idempotently register or update workflow schedules declared by a starting worker."""
        synced: List[WorkflowSchedule] = []
        now = datetime.now(timezone.utc)

        for decl in declarations:
            res = await db.execute(
                select(WorkflowSchedule).where(
                    WorkflowSchedule.project_id == project_id,
                    WorkflowSchedule.workflow_name == decl.workflow_name,
                )
            )
            existing = res.scalar_one_or_none()
            if existing is not None:
                changed = (
                    existing.cron_expression != decl.cron_expression
                    or existing.timezone != decl.timezone
                )
                existing.cron_expression = decl.cron_expression
                existing.timezone = decl.timezone
                if existing.is_active and (changed or existing.next_run_at is None):
                    existing.next_run_at = ScheduleService.calculate_next_run(
                        decl.cron_expression,
                        decl.timezone,
                        base_time=now,
                    )
                synced.append(existing)
            else:
                next_run = ScheduleService.calculate_next_run(
                    decl.cron_expression,
                    decl.timezone,
                    base_time=now,
                )
                schedule = WorkflowSchedule(
                    project_id=project_id,
                    workflow_name=decl.workflow_name,
                    cron_expression=decl.cron_expression,
                    timezone=decl.timezone,
                    is_active=True,
                    next_run_at=next_run,
                )
                try:
                    async with db.begin_nested():
                        db.add(schedule)
                        await db.flush()
                    synced.append(schedule)
                except IntegrityError:
                    retry_res = await db.execute(
                        select(WorkflowSchedule).where(
                            WorkflowSchedule.project_id == project_id,
                            WorkflowSchedule.workflow_name == decl.workflow_name,
                        )
                    )
                    winner = retry_res.scalar_one_or_none()
                    if winner is None:
                        raise
                    winner.cron_expression = decl.cron_expression
                    winner.timezone = decl.timezone
                    if winner.is_active:
                        winner.next_run_at = ScheduleService.calculate_next_run(
                            decl.cron_expression,
                            decl.timezone,
                            base_time=now,
                        )
                    synced.append(winner)

        if synced:
            await db.commit()
            for item in synced:
                await db.refresh(item)

        return synced
