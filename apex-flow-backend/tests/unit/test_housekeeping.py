import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.services.housekeeping import HousekeepingService


@pytest.mark.asyncio
async def test_housekeeping_run_sweep_calls_all_recovery_methods():
    with patch(
        "app.services.housekeeping.housekeeping_service.WorkerService.recover_disconnected_workers",
        new_callable=AsyncMock,
    ) as mock_worker_recover, patch(
        "app.services.housekeeping.housekeeping_service.QueueService.recover_stale_locks",
        new_callable=AsyncMock,
    ) as mock_locks_recover, patch(
        "app.services.housekeeping.housekeeping_service.QueueService.recover_timed_out_workflows",
        new_callable=AsyncMock,
    ) as mock_workflows_recover, patch(
        "app.services.housekeeping.housekeeping_service.ScheduleService.dispatch_due_schedules",
        new_callable=AsyncMock,
    ) as mock_dispatch_schedules, patch(
        "app.services.housekeeping.housekeeping_service.AsyncSessionLocal"
    ) as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        await HousekeepingService.run_sweep()

        mock_worker_recover.assert_awaited_once_with(db=mock_session)
        mock_locks_recover.assert_awaited_once_with(db=mock_session)
        mock_workflows_recover.assert_awaited_once_with(db=mock_session)
        mock_dispatch_schedules.assert_awaited_once_with(db=mock_session)


@pytest.mark.asyncio
async def test_housekeeping_start_and_stop_lifecycle():
    with patch(
        "app.services.housekeeping.housekeeping_service.HousekeepingService.run_sweep",
        new_callable=AsyncMock,
    ) as mock_sweep:
        task = HousekeepingService.start(interval_seconds=0.01)
        assert not task.done()

        await asyncio.sleep(0.03)
        assert mock_sweep.await_count >= 1

        await HousekeepingService.stop(task)
        assert task.done()

