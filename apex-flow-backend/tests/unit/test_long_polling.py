import asyncio
import time
import uuid
from unittest.mock import AsyncMock

import pytest

from app.schemas.step import StepPollRequest
from app.services.steps.notifier import QueueNotifier
from app.services.steps.queue_service import QueueService


@pytest.mark.asyncio
async def test_queue_notifier_timeout_returns_false():
    project_id = uuid.uuid4()
    woken = await QueueNotifier.wait(project_id, timeout_seconds=0.05)
    assert woken is False


@pytest.mark.asyncio
async def test_queue_notifier_instant_notify():
    project_id = uuid.uuid4()

    async def waiter():
        start = time.monotonic()
        woken = await QueueNotifier.wait(project_id, timeout_seconds=5.0)
        return woken, time.monotonic() - start

    task = asyncio.create_task(waiter())
    await asyncio.sleep(0.05)
    QueueNotifier.notify(project_id)

    woken, elapsed = await task
    assert woken is True
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_queue_notifier_delayed_notify():
    project_id = uuid.uuid4()

    async def waiter():
        start = time.monotonic()
        woken = await QueueNotifier.wait(project_id, timeout_seconds=5.0)
        return woken, time.monotonic() - start

    task = asyncio.create_task(waiter())
    await asyncio.sleep(0.02)
    QueueNotifier.notify(project_id, delay_seconds=0.15)

    woken, elapsed = await task
    assert woken is True
    assert 0.1 <= elapsed < 1.0


@pytest.mark.asyncio
async def test_queue_notifier_project_isolation():
    project_a = uuid.uuid4()
    project_b = uuid.uuid4()

    task_a = asyncio.create_task(QueueNotifier.wait(project_a, timeout_seconds=0.12))
    await asyncio.sleep(0.02)
    QueueNotifier.notify(project_b)

    woken_a = await task_a
    assert woken_a is False


@pytest.mark.asyncio
async def test_poll_next_step_wakes_on_notify_without_lost_wakeup(monkeypatch):
    project_id = uuid.uuid4()
    fake_step = object()
    call_count = 0

    async def fake_claim(db, project_id, poll_payload, run_housekeeping=True):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Notify mid-claim to confirm pre-acquired event avoids lost wakeups
            QueueNotifier.notify(project_id)
            return None
        return fake_step

    monkeypatch.setattr(QueueService, "_claim_available_step", staticmethod(fake_claim))

    db = AsyncMock()
    payload = StepPollRequest(timeout_seconds=2.0)
    result = await QueueService.poll_next_step(db=db, project_id=project_id, payload=payload)

    assert result is fake_step
    assert call_count == 2


@pytest.mark.asyncio
async def test_poll_next_step_returns_none_on_timeout(monkeypatch):
    project_id = uuid.uuid4()
    call_count = 0

    async def fake_claim(db, project_id, poll_payload, run_housekeeping=True):
        nonlocal call_count
        call_count += 1
        return None

    monkeypatch.setattr(QueueService, "_claim_available_step", staticmethod(fake_claim))

    db = AsyncMock()
    payload = StepPollRequest(timeout_seconds=0.05)
    start = time.monotonic()
    result = await QueueService.poll_next_step(db=db, project_id=project_id, payload=payload)
    elapsed = time.monotonic() - start

    assert result is None
    assert call_count == 1
    assert elapsed < 0.5

