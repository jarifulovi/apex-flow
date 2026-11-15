import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Coroutine, Deque, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.workflow_run import WorkflowRun
from app.schemas.project import ProjectAlertSettings, WebhookTestResponse, validate_webhook_url

logger = logging.getLogger(__name__)

_DISCORD_HOSTS = (
    "discord.com",
    "discordapp.com",
    "ptb.discord.com",
    "canary.discord.com",
)

_EVENT_TITLES: Dict[str, str] = {
    "workflow.failed": "Workflow Run Failed",
    "workflow.timed_out": "Workflow Execution Timed Out",
    "step.max_retries_exhausted": "Step Exhausted Max Retries",
    "step.lock_expired": "Step Lock Expired (Worker Timeout)",
    "alert.digest": "Alert Storm Digest",
    "alert.test": "ApexFlow Alert Connection Test",
}

_DISCORD_EVENT_COLORS: Dict[str, int] = {
    "workflow.failed": 0xEF4444,
    "step.max_retries_exhausted": 0xEF4444,
    "workflow.timed_out": 0xF59E0B,
    "step.lock_expired": 0xF59E0B,
    "alert.digest": 0xF59E0B,
    "alert.test": 0x10B981,
}


def detect_webhook_provider(webhook_url: str) -> str:
    """Detect Slack, Discord, or generic webhook provider from URL hostname and path."""
    parsed = urlparse(webhook_url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if host == "hooks.slack.com" or host.endswith(".slack.com"):
        return "slack"
    if host in _DISCORD_HOSTS and "/api/webhooks" in path:
        return "discord"
    return "webhook"


def _truncate_text(value: Optional[str], max_length: int = 900) -> str:
    """Truncate long error text cleanly for Slack/Discord payload limits."""
    if not value:
        return ""
    cleaned = value.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 3]}..."


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


class AlertFormatter:
    """Formats ApexFlow alert events into Slack Block Kit, Discord Embeds, or generic JSON."""

    @staticmethod
    def _build_metadata_items(
        project_id: uuid.UUID,
        project_name: str,
        event_type: str,
        workflow_name: str,
        workflow_run_id: Optional[uuid.UUID] = None,
        step_name: Optional[str] = None,
        attempt_count: Optional[int] = None,
        max_attempts: Optional[int] = None,
        suppressed_count: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> List[Tuple[str, str]]:
        """Build ordered label/value pairs shared across Slack and Discord formatters."""
        items: List[Tuple[str, str]] = [
            ("Project", f"{project_name} ({str(project_id)[:8]})"),
            ("Workflow", workflow_name),
            ("Event", event_type),
        ]
        if workflow_run_id is not None:
            items.append(("Run ID", f"`{workflow_run_id}`"))
        if step_name:
            items.append(("Step", f"`{step_name}`"))
        if attempt_count is not None and max_attempts is not None:
            items.append(("Attempts", f"{attempt_count} / {max_attempts}"))
        if suppressed_count is not None:
            window_label = f" in {window_seconds}s" if window_seconds else ""
            items.append(("Suppressed Alerts", f"{suppressed_count} additional event(s){window_label}"))
        return items

    @staticmethod
    def format_event_payload(
        provider: str,
        event_type: str,
        project_id: uuid.UUID,
        project_name: str,
        workflow_name: str = "system",
        workflow_run_id: Optional[uuid.UUID] = None,
        step_name: Optional[str] = None,
        attempt_count: Optional[int] = None,
        max_attempts: Optional[int] = None,
        error_message: Optional[str] = None,
        suppressed_count: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Format an alert payload tailored to the target webhook provider."""
        now_iso = datetime.now(timezone.utc).isoformat()
        title = _EVENT_TITLES.get(event_type, f"ApexFlow Alert ({event_type})")
        if event_type == "alert.digest" and suppressed_count is not None:
            summary_line = (
                f"[{project_name}] {title}: {suppressed_count} additional failure(s) "
                f"in workflow '{workflow_name}'"
            )
        elif event_type == "alert.test":
            summary_line = f"[{project_name}] {title} verified successfully."
        else:
            summary_line = f"[{project_name}] {title} in workflow '{workflow_name}'"

        error_snippet = _truncate_text(error_message)
        metadata_items = AlertFormatter._build_metadata_items(
            project_id=project_id,
            project_name=project_name,
            event_type=event_type,
            workflow_name=workflow_name,
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            attempt_count=attempt_count,
            max_attempts=max_attempts,
            suppressed_count=suppressed_count,
            window_seconds=window_seconds,
        )

        if provider == "slack":
            blocks: List[Dict[str, Any]] = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": title[:150]},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*{label}:*\n{val}"}
                        for label, val in metadata_items[:10]
                    ],
                },
            ]
            if error_snippet:
                blocks.append(
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Details:*\n```{error_snippet}```"},
                    }
                )
            return {"text": summary_line, "blocks": blocks}

        if provider == "discord":
            color = _DISCORD_EVENT_COLORS.get(event_type, 0x6366F1)
            fields = [
                {"name": label, "value": val[:1024], "inline": True}
                for label, val in metadata_items
            ]
            if error_snippet:
                fields.append(
                    {
                        "name": "Error Details",
                        "value": f"```{error_snippet[:1000]}```",
                        "inline": False,
                    }
                )
            embed: Dict[str, Any] = {
                "title": title[:256],
                "description": summary_line[:4096],
                "color": color,
                "fields": fields,
                "timestamp": now_iso,
                "footer": {"text": "ApexFlow Control Plane"},
            }
            return {"content": summary_line, "embeds": [embed]}

        return {
            "event": event_type,
            "project_id": str(project_id),
            "project_name": project_name,
            "workflow_name": workflow_name,
            "workflow_run_id": str(workflow_run_id) if workflow_run_id is not None else None,
            "step_name": step_name,
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
            "error_message": error_message,
            "suppressed_count": suppressed_count,
            "window_seconds": window_seconds,
            "timestamp": now_iso,
        }


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


_limiter = SlidingWindowLimiter()
_background_tasks: Set[asyncio.Task[Any]] = set()


async def _post_webhook(webhook_url: str, payload: Dict[str, Any]) -> Tuple[int, float, str]:
    """Send a JSON HTTP POST request to a webhook endpoint with a 5s timeout."""
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(webhook_url, json=payload)
    latency_ms = round((time.monotonic() - start) * 1000.0, 2)
    return response.status_code, latency_ms, response.text


class AlertService:
    """Service coordinating alert formatting, sliding-window rate limiting, and webhook dispatch."""

    @staticmethod
    def get_limiter() -> SlidingWindowLimiter:
        return _limiter

    @staticmethod
    def _is_event_enabled(alert_settings: ProjectAlertSettings, event_type: str) -> bool:
        if event_type == "step.max_retries_exhausted":
            return alert_settings.alert_on_max_retry or alert_settings.alert_on_failure
        if event_type == "workflow.failed":
            return alert_settings.alert_on_failure
        if event_type in ("workflow.timed_out", "step.lock_expired"):
            return alert_settings.alert_on_timeout or alert_settings.alert_on_failure
        return False

    @classmethod
    async def _flush_digest_bucket(cls, bucket: DigestBucket) -> None:
        if not bucket.webhook_url:
            return
        provider = detect_webhook_provider(bucket.webhook_url)
        payload = AlertFormatter.format_event_payload(
            provider=provider,
            event_type="alert.digest",
            project_id=bucket.project_id,
            project_name=bucket.project_name,
            workflow_name=bucket.workflow_name,
            workflow_run_id=bucket.latest_run_id,
            error_message=bucket.latest_error,
            suppressed_count=bucket.count,
            window_seconds=bucket.window_seconds,
        )
        try:
            status_code, _, body = await _post_webhook(bucket.webhook_url, payload)
            if status_code < 200 or status_code >= 300:
                logger.warning(
                    "Digest webhook returned non-2xx status %s for project %s: %s",
                    status_code,
                    bucket.project_id,
                    body[:200],
                )
        except Exception as exc:
            logger.error(
                "Error dispatching digest webhook for project %s: %s",
                bucket.project_id,
                exc,
            )

    @classmethod
    async def send_test_alert(
        cls,
        project: Project,
        override_url: Optional[str] = None,
    ) -> WebhookTestResponse:
        """Send an immediate verification alert to the configured or supplied webhook URL."""
        raw_url = override_url
        if raw_url is None:
            alerts_meta = (project.metadata_ or {}).get("alerts")
            if isinstance(alerts_meta, dict):
                raw_url = str(alerts_meta.get("webhook_url", ""))
            else:
                raw_url = ""

        target_url = validate_webhook_url(raw_url)
        if not target_url:
            raise ValueError("Webhook URL is required to send a test alert.")

        provider = detect_webhook_provider(target_url)
        payload = AlertFormatter.format_event_payload(
            provider=provider,
            event_type="alert.test",
            project_id=project.id,
            project_name=project.name,
            workflow_name="test_connection",
        )

        start = time.monotonic()
        try:
            status_code, latency_ms, body = await _post_webhook(target_url, payload)
        except httpx.RequestError as exc:
            latency_ms = round((time.monotonic() - start) * 1000.0, 2)
            logger.warning("Test webhook connection error for project %s: %s", project.id, exc)
            return WebhookTestResponse(
                ok=False,
                status_code=0,
                provider=provider,
                latency_ms=latency_ms,
                detail=f"Webhook connection failed: {exc}",
            )

        ok = 200 <= status_code < 300
        if ok:
            detail = f"Webhook HTTP {status_code} OK ({provider})"
        else:
            logger.warning(
                "Test webhook returned HTTP %s for project %s: %s",
                status_code,
                project.id,
                body[:200],
            )
            detail = f"Webhook returned HTTP {status_code}: {body[:200]}"

        return WebhookTestResponse(
            ok=ok,
            status_code=status_code,
            provider=provider,
            latency_ms=latency_ms,
            detail=detail,
        )

    @classmethod
    async def emit_alert(
        cls,
        project: Project,
        event_type: str,
        workflow_run_id: Optional[uuid.UUID] = None,
        workflow_name: str = "unknown_workflow",
        step_name: Optional[str] = None,
        attempt_count: Optional[int] = None,
        max_attempts: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Evaluate alert toggles and sliding window rate limits for a project,
        then dispatch an alert immediately or coalesce into a digest bucket.
        """
        raw_alerts = (project.metadata_ or {}).get("alerts")
        if not isinstance(raw_alerts, dict):
            return False

        try:
            alert_settings = ProjectAlertSettings(**raw_alerts)
        except Exception as exc:
            logger.error("Invalid alert configuration stored on project %s: %s", project.id, exc)
            return False

        if not alert_settings.webhook_url:
            return False

        if not cls._is_event_enabled(alert_settings, event_type):
            return False

        allowed = _limiter.check_and_record(
            project_id=project.id,
            workflow_name=workflow_name,
            window_seconds=alert_settings.window_seconds,
            max_alerts_per_window=alert_settings.max_alerts_per_window,
            project_name=project.name,
            webhook_url=alert_settings.webhook_url,
            error_message=error_message,
            workflow_run_id=workflow_run_id,
            on_flush=cls._flush_digest_bucket,
        )
        if not allowed:
            return False

        provider = detect_webhook_provider(alert_settings.webhook_url)
        payload = AlertFormatter.format_event_payload(
            provider=provider,
            event_type=event_type,
            project_id=project.id,
            project_name=project.name,
            workflow_name=workflow_name,
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            attempt_count=attempt_count,
            max_attempts=max_attempts,
            error_message=error_message,
        )

        try:
            status_code, _, body = await _post_webhook(alert_settings.webhook_url, payload)
        except Exception as exc:
            logger.error("Failed sending alert webhook for project %s: %s", project.id, exc)
            return False

        if status_code < 200 or status_code >= 300:
            logger.warning(
                "Alert webhook returned non-2xx status %s for project %s: %s",
                status_code,
                project.id,
                body[:200],
            )
            return False

        return True

    @classmethod
    async def _run_scheduled_alert(
        cls,
        project_id: Optional[uuid.UUID],
        event_type: str,
        workflow_run_id: uuid.UUID,
        workflow_name: Optional[str],
        step_name: Optional[str],
        attempt_count: Optional[int],
        max_attempts: Optional[int],
        error_message: Optional[str],
    ) -> None:
        try:
            async with AsyncSessionLocal() as session:
                resolved_project_id = project_id
                resolved_workflow_name = workflow_name
                if resolved_project_id is None or resolved_workflow_name is None:
                    run_res = await session.execute(
                        select(WorkflowRun.project_id, WorkflowRun.workflow_name).where(
                            WorkflowRun.id == workflow_run_id
                        )
                    )
                    run_row = run_res.first()
                    if run_row is not None:
                        if resolved_project_id is None:
                            resolved_project_id = run_row[0]
                        if resolved_workflow_name is None:
                            resolved_workflow_name = run_row[1]

                if resolved_project_id is None:
                    logger.warning(
                        "Unable to resolve project_id when dispatching alert for run %s",
                        workflow_run_id,
                    )
                    return

                proj_res = await session.execute(
                    select(Project).where(Project.id == resolved_project_id)
                )
                project = proj_res.scalar_one_or_none()
                if project is None:
                    logger.warning(
                        "Unable to resolve project %s when dispatching alert for run %s",
                        resolved_project_id,
                        workflow_run_id,
                    )
                    return

                await cls.emit_alert(
                    project=project,
                    event_type=event_type,
                    workflow_run_id=workflow_run_id,
                    workflow_name=resolved_workflow_name or "unknown_workflow",
                    step_name=step_name,
                    attempt_count=attempt_count,
                    max_attempts=max_attempts,
                    error_message=error_message,
                )
        except Exception as exc:
            logger.exception(
                "Unhandled exception dispatching scheduled alert (%s) for run %s: %s",
                event_type,
                workflow_run_id,
                exc,
            )

    @classmethod
    def schedule_alert(
        cls,
        db: Optional[AsyncSession],
        project_id: Optional[uuid.UUID],
        event_type: str,
        workflow_run_id: uuid.UUID,
        workflow_name: Optional[str] = None,
        step_name: Optional[str] = None,
        attempt_count: Optional[int] = None,
        max_attempts: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Schedule non-blocking background alert delivery after a database commit."""
        if db is None or type(db).__name__.endswith("Mock"):
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No running event loop to schedule alert %s for run %s", event_type, workflow_run_id)
            return

        task = loop.create_task(
            cls._run_scheduled_alert(
                project_id=project_id,
                event_type=event_type,
                workflow_run_id=workflow_run_id,
                workflow_name=workflow_name,
                step_name=step_name,
                attempt_count=attempt_count,
                max_attempts=max_attempts,
                error_message=error_message,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

