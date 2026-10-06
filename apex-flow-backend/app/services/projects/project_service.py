import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.project import Project
from app.models.project_key import ProjectKey
from app.models.step import WorkflowStep
from app.models.worker import Worker
from app.models.workflow_run import WorkflowRun
from app.schemas.project import (
    ActivityItemResponse,
    ProjectCreate,
    ProjectMetricsResponse,
    ProjectOverviewResponse,
)


class ProjectService:
    @staticmethod
    async def create_project(
        db: AsyncSession,
        owner_id: uuid.UUID,
        payload: ProjectCreate,
    ) -> Project:
        """Create a new project for a user with duplicate name check."""
        existing = await db.execute(
            select(Project).where(Project.owner_id == owner_id, Project.name == payload.name)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"A project named '{payload.name}' already exists.")

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
        """List all projects belonging to an owner. Auto-creates Default Project if none exist."""
        query = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
        )
        result = await db.execute(query)
        projects = list(result.scalars().all())

        if not projects:
            default_proj = await ProjectService.get_or_create_default_project(db=db, owner_id=owner_id)
            return [default_proj]

        return projects

    @staticmethod
    async def delete_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> None:
        """Delete a project by ID, forbidding deletion of default project."""
        project = await ProjectService.get_project_by_id(db=db, project_id=project_id, owner_id=owner_id)

        if project.name == "Default Project" or (project.metadata_ and project.metadata_.get("is_default")):
            raise ValueError("The Default Project cannot be deleted.")

        await db.delete(project)
        await db.commit()

    @staticmethod
    async def get_or_create_default_project(
        db: AsyncSession,
        owner_id: uuid.UUID,
    ) -> Project:
        """Get or automatically create a single Default Project for a user."""
        query = (
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.asc())
        )
        result = await db.execute(query)
        projects = list(result.scalars().all())

        if projects:
            default_proj = next(
                (p for p in projects if p.name == "Default Project" or (p.metadata_ and p.metadata_.get("is_default"))),
                projects[0],
            )
            return default_proj

        try:
            project = Project(
                owner_id=owner_id,
                name="Default Project",
                metadata_={"is_default": True},
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            return project
        except Exception:
            await db.rollback()
            fallback_res = await db.execute(
                select(Project).where(Project.owner_id == owner_id).order_by(Project.created_at.asc()).limit(1)
            )
            return fallback_res.scalar_one()

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
            success_rate = 0.0

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

    @staticmethod
    async def get_project_overview(
        db: AsyncSession,
        project_id: uuid.UUID,
        owner_id: Optional[uuid.UUID] = None,
    ) -> ProjectOverviewResponse:
        """Fetch consolidated project telemetry, metrics, and recent activity in 1 single retrieval."""
        stats = await ProjectService.get_project_metrics(db=db, project_id=project_id, owner_id=owner_id)

        # 1. Fetch 6 most recent step activity items
        step_query = (
            select(WorkflowStep)
            .join(WorkflowRun, WorkflowStep.workflow_run_id == WorkflowRun.id)
            .where(WorkflowRun.project_id == project_id)
            .order_by(WorkflowStep.created_at.desc())
            .limit(6)
        )
        step_res = await db.execute(step_query)
        recent_steps = list(step_res.scalars().all())

        activities = [
            ActivityItemResponse(
                id=s.id,
                workflow_id=str(s.workflow_run_id),
                step_name=s.step_name,
                status=s.status,
                timestamp=s.updated_at or s.created_at,
                error_message=s.error_message,
            )
            for s in recent_steps
        ]

        # 2. Check key existence
        key_query = select(func.count(ProjectKey.id)).where(
            ProjectKey.project_id == project_id,
            ProjectKey.status == "active",
        )
        key_res = await db.execute(key_query)
        keys_count = key_res.scalar() or 0

        return ProjectOverviewResponse(
            stats=stats,
            activities=activities,
            has_keys=keys_count > 0,
            has_workflows=stats.total_runs > 0,
        )

