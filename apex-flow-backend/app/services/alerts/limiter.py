import asyncio
from collections import deque
from dataclasses import dataclass
import logging
import time
from typing import Any, Callable, Coroutine, Deque, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


@dataclass
class DigestBucket:
    """Holds coalesced alert metadata accumulated while a sliding window is saturated."""

    project_id: uuid.UUID
    project_name: str
    webhook_url: str
    workflow_name: str
    window_seconds: int
    count: int = 0
    latest_error: Optional[str] = None
    latest_run_id: Optional[uuid.UUID] = None
    flush_task: Optional[asyncio.Task[Any]] = None


class SlidingWindowLimiter:
    """
    Per-(project_id, workflow_name) sliding window rate limiter with a project-wide ceiling
    and digest coalescing for suppressed alerts.
    """

    def __init__(self) -> None:
        self._workflow_windows: Dict[Tuple[uuid.UUID, str], Deque[float]] = {}
        self._project_windows: Dict[uuid.UUID, Deque[float]] = {}
        self._suppressed_digests: Dict[Tuple[uuid.UUID, str], DigestBucket] = {}

    def reset(self) -> None:
        """Cancel pending digest tasks and clear all window state (primarily for tests)."""
        for bucket in self._suppressed_digests.values():
            if bucket.flush_task is not None and not bucket.flush_task.done():
                bucket.flush_task.cancel()
        self._workflow_windows.clear()
        self._project_windows.clear()
        self._suppressed_digests.clear()

    def pop_digest(self, project_id: uuid.UUID, workflow_name: str) -> Optional[DigestBucket]:
        """Remove and return any pending suppressed digest bucket for a workflow."""
        return self._suppressed_digests.pop((project_id, workflow_name), None)

    def _prune_window(self, window: Deque[float], cutoff: float) -> None:
        while window and window[0] <= cutoff:
            window.popleft()

    def check_and_record(
        self,
        project_id: uuid.UUID,
        workflow_name: str,
        window_seconds: int,
        max_alerts_per_window: int,
        project_name: str = "",
        webhook_url: str = "",
        error_message: Optional[str] = None,
        workflow_run_id: Optional[uuid.UUID] = None,
        now_mono: Optional[float] = None,
        on_flush: Optional[Callable[[DigestBucket], Coroutine[Any, Any, None]]] = None,
    ) -> bool:
        """
        Check whether an alert is permitted under the sliding window limits.
        If allowed, records the timestamp and returns True.
        If throttled, increments the digest bucket and returns False.
        """
        now = now_mono if now_mono is not None else time.monotonic()
        cutoff = now - window_seconds

        wf_key = (project_id, workflow_name)
        wf_window = self._workflow_windows.setdefault(wf_key, deque())
        proj_window = self._project_windows.setdefault(project_id, deque())

        self._prune_window(wf_window, cutoff)
        self._prune_window(proj_window, cutoff)

        project_ceiling = max_alerts_per_window * 3
        wf_under_limit = len(wf_window) < max_alerts_per_window
        proj_under_limit = len(proj_window) < project_ceiling

        if wf_under_limit and proj_under_limit:
            wf_window.append(now)
            proj_window.append(now)
            return True

        # Compute earliest time a slot will open up for digest delivery
        candidate_expiries: List[float] = []
        if not wf_under_limit and wf_window:
            candidate_expiries.append(wf_window[0] + window_seconds)
        if not proj_under_limit and proj_window:
            candidate_expiries.append(proj_window[0] + window_seconds)
        next_slot = min(candidate_expiries) if candidate_expiries else now + window_seconds
        delay_seconds = max(0.05, next_slot - now)

        bucket = self._suppressed_digests.get(wf_key)
        if bucket is None:
            bucket = DigestBucket(
                project_id=project_id,
                project_name=project_name,
                webhook_url=webhook_url,
                workflow_name=workflow_name,
                window_seconds=window_seconds,
            )
            self._suppressed_digests[wf_key] = bucket

        bucket.count += 1
        bucket.project_name = project_name or bucket.project_name
        bucket.webhook_url = webhook_url or bucket.webhook_url
        bucket.window_seconds = window_seconds
        if error_message:
            bucket.latest_error = error_message
        if workflow_run_id is not None:
            bucket.latest_run_id = workflow_run_id

        if on_flush is not None and (bucket.flush_task is None or bucket.flush_task.done()):
            try:
                loop = asyncio.get_running_loop()
                bucket.flush_task = loop.create_task(
                    self._flush_after_delay(wf_key, delay_seconds, on_flush)
                )
            except RuntimeError:
                pass

        return False

    async def _flush_after_delay(
        self,
        wf_key: Tuple[uuid.UUID, str],
        delay_seconds: float,
        on_flush: Callable[[DigestBucket], Coroutine[Any, Any, None]],
    ) -> None:
        try:
            await asyncio.sleep(delay_seconds)
            bucket = self._suppressed_digests.pop(wf_key, None)
            if bucket is None or bucket.count <= 0:
                return

            now = time.monotonic()
            cutoff = now - bucket.window_seconds
            wf_window = self._workflow_windows.setdefault(wf_key, deque())
            proj_window = self._project_windows.setdefault(bucket.project_id, deque())
            self._prune_window(wf_window, cutoff)
            self._prune_window(proj_window, cutoff)
            wf_window.append(now)
            proj_window.append(now)

            await on_flush(bucket)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Failed flushing alert digest for %s: %s", wf_key, exc)

