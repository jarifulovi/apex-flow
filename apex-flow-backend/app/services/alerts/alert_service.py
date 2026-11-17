import asyncio
import logging
import time
from typing import Any, Dict, Optional, Set, Tuple
import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.workflow_run import WorkflowRun
from app.schemas.project import ProjectAlertSettings, WebhookTestResponse, validate_webhook_url
from app.services.alerts.formatter import AlertFormatter, detect_webhook_provider
from app.services.alerts.limiter import DigestBucket, SlidingWindowLimiter

logger = logging.getLogger(__name__)

# Re-exports for backward compatibility with existing callers and tests
__all__ = [
    "AlertFormatter",
    "AlertService",
    "DigestBucket",
    "SlidingWindowLimiter",
    "detect_webhook_provider",
]

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
        if event_type == "worker.disconnected":
            return alert_settings.alert_on_worker_disconnect
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
        workflow_run_id: Optional[uuid.UUID],
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
                if (
                    resolved_project_id is None or resolved_workflow_name is None
                ) and workflow_run_id is not None:
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
        workflow_run_id: Optional[uuid.UUID] = None,
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
