import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worker import Worker
from app.schemas.worker import WorkerHeartbeatRequest


class WorkerService:
    @staticmethod
    async def register_or_heartbeat(
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: WorkerHeartbeatRequest,
    ) -> Worker:
        """Register a new worker runtime or update heartbeat timestamp of an existing worker."""
        now = datetime.now(timezone.utc)

        if payload.worker_id:
            query = select(Worker).where(
                Worker.id == payload.worker_id,
                Worker.project_id == project_id,
            )
            result = await db.execute(query)
            worker = result.scalar_one_or_none()
            if worker:
                worker.last_seen_at = now
                worker.status = "active"
                if payload.name:
                    worker.name = payload.name
                await db.commit()
                await db.refresh(worker)
                return worker

        # Check by name under project if worker_id is missing or not found
        query = select(Worker).where(
            Worker.project_id == project_id,
            Worker.name == payload.name,
        )
        result = await db.execute(query)
        worker = result.scalar_one_or_none()

        if worker:
            worker.last_seen_at = now
            worker.status = "active"
        else:
            worker = Worker(
                project_id=project_id,
                name=payload.name,
                status="active",
                last_seen_at=now,
            )
            db.add(worker)

        await db.commit()
        await db.refresh(worker)
        return worker

    @staticmethod
    async def list_workers(
        db: AsyncSession,
        project_id: Optional[uuid.UUID] = None,
        owner_id: Optional[uuid.UUID] = None,
    ) -> List[Worker]:
        """List active or registered workers for a project/owner."""
        query = select(Worker).order_by(Worker.last_seen_at.desc().nulls_last())

        if project_id:
            query = query.where(Worker.project_id == project_id)
        elif owner_id:
            query = query.join(Worker.project).where(Worker.project.has(owner_id=owner_id))

        result = await db.execute(query)
        return list(result.scalars().all())
