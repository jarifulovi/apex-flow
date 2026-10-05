import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.project import Project
from app.models.worker import Worker
from app.models.workflow_run import WorkflowRun
from app.schemas.project import ProjectCreate, ProjectMetricsResponse


class ProjectService:
    @staticmethod
    async def create_project(
        db: AsyncSession,
        owner_id: uuid.UUID,
        payload: ProjectCreate,
    ) -> Project:
        """Create a new project for a user."""
        project = Project(
            owner_id=owner_id,
            name=payload.name,
            metadata_=payload.metadata or {},
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        owner_id: uuid.UUID,
    ) -> List[Project]:
        """List all projects belonging to an owner."""
        query = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_or_create_default_project(
        db: AsyncSession,
        owner_id: uuid.UUID,
    ) -> Project:
        """Get or automatically create a Default Project for a user."""
        query = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.asc())
            .limit(1)
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            project = Project(
                owner_id=owner_id,
                name="Default Project",
                metadata_={"is_default": True},
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)

        return project

    @staticmethod
    async def get_project_by_id(
        db: AsyncSession,
        project_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
    ) -> Project:
        """Fetch project details by ID with optional owner scoping."""
        query = select(Project).where(Project.id == project_id)
        if owner_id:
            query = query.where(Project.owner_id == owner_id)

        result = await db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            raise EntityNotFoundException("Project", project_id)

        return project

    @staticmethod
    async def get_project_metrics(
        db: AsyncSession,
        project_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
    ) -> ProjectMetricsResponse:
        """Calculate live project metrics and telemetry summary."""
        # Ensure project exists & user owns it if owner_id provided
        await ProjectService.get_project_by_id(db=db, project_id=project_id, owner_id=owner_id)

        now = datetime.now(timezone.utc)
        five_min_ago = now - timedelta(minutes=5)

        # 1. Query workflow run counts grouped by status
        status_query = (
            select(WorkflowRun.status, func.count(WorkflowRun.id))
            .where(WorkflowRun.project_id == project_id)
            .group_by(WorkflowRun.status)
        )
        status_res = await db.execute(status_query)
        status_counts = dict(status_res.fetchall())

        completed_runs = status_counts.get("completed", 0)
        failed_runs = status_counts.get("failed", 0)
        running_runs = status_counts.get("running", 0)
        cancelled_runs = status_counts.get("cancelled", 0)
        total_runs = sum(status_counts.values())

        # 2. Calculate success rate %
        terminal_runs = completed_runs + failed_runs
        if terminal_runs > 0:
            success_rate = round((completed_runs / terminal_runs) * 100, 1)
        elif total_runs > 0:
            success_rate = round((completed_runs / total_runs) * 100, 1)
        else:
            success_rate = 100.0

        # 3. Active workers count (last seen within 5 minutes)
        worker_query = select(func.count(Worker.id)).where(
            Worker.project_id == project_id,
            Worker.status == "active",
            Worker.last_seen_at.is_not(None),
            Worker.last_seen_at >= five_min_ago,
        )
        worker_res = await db.execute(worker_query)
        active_workers = worker_res.scalar() or 0

        # 4. Average completed duration in seconds
        avg_dur_query = select(
            func.avg(
                func.extract("epoch", WorkflowRun.completed_at) - func.extract("epoch", WorkflowRun.started_at)
            )
        ).where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.status == "completed",
            WorkflowRun.started_at.is_not(None),
            WorkflowRun.completed_at.is_not(None),
        )
        avg_res = await db.execute(avg_dur_query)
        avg_dur = avg_res.scalar() or 0.0
        avg_duration_seconds = round(float(avg_dur), 2)

        return ProjectMetricsResponse(
            project_id=project_id,
            total_runs=total_runs,
            completed_runs=completed_runs,
            failed_runs=failed_runs,
            running_runs=running_runs,
            cancelled_runs=cancelled_runs,
            success_rate_percent=success_rate,
            active_workers_count=active_workers,
            avg_duration_seconds=avg_duration_seconds,
        )
