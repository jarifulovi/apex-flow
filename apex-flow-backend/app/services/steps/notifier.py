import asyncio
import uuid
import weakref
from typing import Dict, Optional


class QueueNotifier:
    """In-memory per-project wakeup notifier for FastAPI asyncio long-polling."""

    _loop_events: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Dict[uuid.UUID, asyncio.Event]]" = (
        weakref.WeakKeyDictionary()
    )
    _loop_waiters: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Dict[uuid.UUID, int]]" = (
        weakref.WeakKeyDictionary()
    )

    @classmethod
    def is_waiting(cls, project_id: uuid.UUID) -> bool:
        """Return True if at least one coroutine is currently suspended in wait() for project_id."""
        loop = asyncio.get_running_loop()
        waiters = cls._loop_waiters.get(loop)
        return bool(waiters and waiters.get(project_id, 0) > 0)

    @classmethod
    def get_event(cls, project_id: uuid.UUID) -> asyncio.Event:
        """Return the current wakeup event for project_id on the active event loop."""
        loop = asyncio.get_running_loop()
        events = cls._loop_events.setdefault(loop, {})
        event = events.get(project_id)
        if event is None:
            event = asyncio.Event()
            events[project_id] = event
        return event

    @classmethod
    def _trigger(cls, project_id: uuid.UUID) -> None:
        loop = asyncio.get_running_loop()
        events = cls._loop_events.get(loop)
        if not events:
            return
        event = events.pop(project_id, None)
        if event is not None:
            event.set()

    @classmethod
    def notify(cls, project_id: uuid.UUID, delay_seconds: float = 0.0) -> None:
        """Wake waiting workers for a project immediately or after delay_seconds."""
        loop = asyncio.get_running_loop()
        if delay_seconds > 0:
            loop.call_later(delay_seconds, cls._trigger, project_id)
            return
        cls._trigger(project_id)

    @classmethod
    async def wait(
        cls,
        project_id: uuid.UUID,
        timeout_seconds: float,
        event: Optional[asyncio.Event] = None,
    ) -> bool:
        """Wait until notified or timeout_seconds elapses. Returns True if notified."""
        if timeout_seconds <= 0:
            return False
        loop = asyncio.get_running_loop()
        waiters = cls._loop_waiters.setdefault(loop, {})
        waiters[project_id] = waiters.get(project_id, 0) + 1
        target = event or cls.get_event(project_id)
        try:
            await asyncio.wait_for(target.wait(), timeout=timeout_seconds)
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            remaining = waiters.get(project_id, 1) - 1
            if remaining > 0:
                waiters[project_id] = remaining
            else:
                waiters.pop(project_id, None)

