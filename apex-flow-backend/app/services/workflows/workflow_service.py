import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EntityNotFoundException
from app.models.workflow_run import WorkflowRun
from app.models.step import WorkflowStep
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

        if payload.deduplication_id:
            stmt = select(WorkflowRun).where(
                WorkflowRun.project_id == target_project_id,
                WorkflowRun.deduplication_id == payload.deduplication_id,
                WorkflowRun.status.in_(["pending", "running"]),
            )
            res = await db.execute(stmt)
            existing_run = res.scalar_one_or_none()
            if existing_run:
                return existing_run

        now = datetime.now(timezone.utc)
        deadline = None
        if payload.timeout_seconds and payload.timeout_seconds > 0:
            deadline = now + timedelta(seconds=payload.timeout_seconds)

        workflow_run = WorkflowRun(
            project_id=target_project_id,
            workflow_name=payload.workflow_name,
            status="pending",
            metadata_=payload.metadata or {},
            deduplication_id=payload.deduplication_id,
            parent_workflow_id=payload.parent_workflow_id,
            timeout_seconds=payload.timeout_seconds,
            deadline_at=deadline,
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
        status: Optional[str] = None,
        workflow_name: Optional[str] = None,
        parent_workflow_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[WorkflowRun], int]:
        """List workflow runs with optional project, status, owner, search, or parent_workflow_id filtering."""
        filters = []
        if project_id:
            filters.append(WorkflowRun.project_id == project_id)
        elif owner_id:
            filters.append(WorkflowRun.project.has(owner_id=owner_id))

        if status and status.lower() != "all":
            filters.append(WorkflowRun.status == status.lower())

        if workflow_name:
            filters.append(WorkflowRun.workflow_name == workflow_name)

        if parent_workflow_id:
            filters.append(WorkflowRun.parent_workflow_id == parent_workflow_id)

        if search:
            pattern = f"%{search.lower().strip()}%"
            filters.append(
                or_(
                    func.lower(WorkflowRun.workflow_name).like(pattern),
                    func.lower(cast(WorkflowRun.id, String)).like(pattern),
                    func.lower(func.coalesce(WorkflowRun.deduplication_id, "")).like(pattern),
                )
            )

        # Count query
        count_stmt = select(func.count(WorkflowRun.id))
        if filters:
            if owner_id and not project_id:
                count_stmt = count_stmt.join(WorkflowRun.project).where(*filters)
            else:
                count_stmt = count_stmt.where(*filters)

        total_count_res = await db.execute(count_stmt)
        total_count = total_count_res.scalar() or 0

        # Items query
        query = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.steps))
            .order_by(WorkflowRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            if owner_id and not project_id:
                query = query.join(WorkflowRun.project).where(*filters)
            else:
                query = query.where(*filters)

        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total_count

    @staticmethod
    async def get_workflow_status_counts(
        db: AsyncSession,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, int]:
        """Get workflow count per status for filter tabs."""
        stmt = select(WorkflowRun.status, func.count(WorkflowRun.id)).group_by(WorkflowRun.status)
        if project_id:
            stmt = stmt.where(WorkflowRun.project_id == project_id)
        elif owner_id:
            stmt = stmt.join(WorkflowRun.project).where(WorkflowRun.project.has(owner_id=owner_id))

        result = await db.execute(stmt)
        counts: Dict[str, int] = {"all": 0, "pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}
        total = 0
        for status_val, count_val in result.all():
            if status_val in counts:
                counts[status_val] = count_val
            total += count_val
        counts["all"] = total
        return counts

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

        # Enforce execution timeout if deadline has passed
        now = datetime.now(timezone.utc)
        if (
            workflow_run.status in ("pending", "running")
            and workflow_run.deadline_at
            and workflow_run.deadline_at <= now
        ):
            workflow_run.status = "failed"
            workflow_run.completed_at = now
            workflow_run.error_message = (
                f"Workflow execution timed out (exceeded {workflow_run.timeout_seconds}s limit)."
            )
            for step in workflow_run.steps:
                if step.status in ("queued", "running"):
                    step.status = "cancelled"
                    step.completed_at = now
                    step.error_message = "Cancelled due to workflow timeout."
                    step.locked_until = None
            await db.commit()
            await db.refresh(workflow_run)

        # Fetch child sub-workflows for workflow detail in 1 DB query
        sub_query = (
            select(WorkflowRun)
            .where(WorkflowRun.parent_workflow_id == workflow_run_id)
            .options(selectinload(WorkflowRun.steps))
            .order_by(WorkflowRun.created_at.asc())
        )
        sub_res = await db.execute(sub_query)
        setattr(workflow_run, "sub_workflows", list(sub_res.scalars().all()))

        return workflow_run

    @staticmethod
    async def cancel_workflow_run(
        db: AsyncSession,
        workflow_run_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> WorkflowRun:
        """Cancel an active workflow run, its pending steps, and cascade cancel to child sub-workflows."""
        workflow_run = await WorkflowService.get_workflow_run_by_id(
            db=db, workflow_run_id=workflow_run_id, owner_id=owner_id, project_id=project_id
        )

        now = datetime.now(timezone.utc)
        workflow_run.status = "cancelled"
        workflow_run.completed_at = now

        # Update loaded steps for this workflow run
        for step in workflow_run.steps:
            if step.status in ("queued", "running"):
                step.status = "cancelled"
                step.locked_until = None
                step.completed_at = now

        # Cascade cancel to child sub-workflows
        await db.execute(
            update(WorkflowRun)
            .where(
                WorkflowRun.parent_workflow_id == workflow_run_id,
                WorkflowRun.status.in_(["pending", "running"]),
            )
            .values(status="cancelled", completed_at=now)
            .execution_options(synchronize_session=False)
        )

        await db.commit()
        await db.refresh(workflow_run)
        return workflow_run

    @staticmethod
    async def restart_workflow_run(
        db: AsyncSession,
        workflow_run_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> WorkflowRun:
        """Reset failed or cancelled steps to queued, restart workflow run, and reset child sub-workflows."""
        workflow_run = await WorkflowService.get_workflow_run_by_id(
            db=db, workflow_run_id=workflow_run_id, owner_id=owner_id, project_id=project_id
        )

        now = datetime.now(timezone.utc)
        workflow_run.status = "running"
        workflow_run.completed_at = None
        workflow_run.started_at = now
        workflow_run.error_message = None
        if workflow_run.timeout_seconds and workflow_run.timeout_seconds > 0:
            workflow_run.deadline_at = now + timedelta(seconds=workflow_run.timeout_seconds)
        else:
            workflow_run.deadline_at = None

        # Reset failed/cancelled steps to queued
        for step in workflow_run.steps:
            if step.status in ("failed", "cancelled"):
                step.status = "queued"
                step.attempt_count = 0
                step.error_message = None
                step.locked_until = None
                step.completed_at = None
                step.available_at = now

        # Cascade reset to child sub-workflows if failed or cancelled
        await db.execute(
            update(WorkflowRun)
            .where(
                WorkflowRun.parent_workflow_id == workflow_run_id,
                WorkflowRun.status.in_(["failed", "cancelled"]),
            )
            .values(status="pending", completed_at=None)
            .execution_options(synchronize_session=False)
        )

        await db.commit()
        await db.refresh(workflow_run)
        return workflow_run

    @staticmethod
    async def complete_workflow_run(
        db: AsyncSession,
        workflow_run_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> WorkflowRun:
        """Explicitly mark a workflow run as completed if no child steps failed or cancelled."""
        workflow_run = await WorkflowService.get_workflow_run_by_id(
            db=db, workflow_run_id=workflow_run_id, owner_id=owner_id, project_id=project_id
        )

        now = datetime.now(timezone.utc)
        has_failed_steps = any(s.status in ("failed", "cancelled") for s in workflow_run.steps)

        if has_failed_steps or workflow_run.status in ("failed", "cancelled"):
            workflow_run.status = "failed" if workflow_run.status != "cancelled" else "cancelled"
            workflow_run.completed_at = now
        else:
            workflow_run.status = "completed"
            workflow_run.completed_at = now

        await db.commit()
        await db.refresh(workflow_run)
        return workflow_run

