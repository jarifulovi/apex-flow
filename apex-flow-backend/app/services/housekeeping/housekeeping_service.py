import asyncio
from contextlib import suppress
import logging
from typing import Optional

from app.core.database import AsyncSessionLocal
from app.services.steps import QueueService
from app.services.workers import WorkerService

logger = logging.getLogger(__name__)


class HousekeepingService:
    """Coordinates periodic background sweeps for worker disconnects, lock expiration, and timeouts."""

    @staticmethod
    async def run_sweep() -> None:
        """Reconcile disconnected workers, expired step locks, and timed-out workflow runs."""
        async with AsyncSessionLocal() as session:
            await WorkerService.recover_disconnected_workers(db=session)
            await QueueService.recover_stale_locks(db=session)
            await QueueService.recover_timed_out_workflows(db=session)

    @classmethod
    async def run_loop(cls, interval_seconds: float = 30.0) -> None:
        """Periodic background sweeper ensuring timeouts and disconnects are caught when 0 workers poll."""
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                await cls.run_sweep()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Unhandled error during background housekeeping sweep: %s", exc)

    @classmethod
    def start(cls, interval_seconds: float = 30.0) -> asyncio.Task:
        """Start the background housekeeping sweeper task."""
        return asyncio.create_task(cls.run_loop(interval_seconds=interval_seconds))

    @staticmethod
    async def stop(task: Optional[asyncio.Task]) -> None:
        """Gracefully stop and await the background housekeeping sweeper task."""
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

