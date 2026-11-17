from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import uuid

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
    "worker.disconnected": "Worker Heartbeat Disconnected",
    "alert.digest": "Alert Storm Digest",
    "alert.test": "ApexFlow Alert Connection Test",
}

_DISCORD_EVENT_COLORS: Dict[str, int] = {
    "workflow.failed": 0xEF4444,
    "step.max_retries_exhausted": 0xEF4444,
    "workflow.timed_out": 0xF59E0B,
    "step.lock_expired": 0xF59E0B,
    "worker.disconnected": 0xF59E0B,
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
        target_label = "Worker" if event_type == "worker.disconnected" else "Workflow"
        items: List[Tuple[str, str]] = [
            ("Project", f"{project_name} ({str(project_id)[:8]})"),
            (target_label, workflow_name),
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
        elif event_type == "worker.disconnected":
            summary_line = (
                f"[{project_name}] {title}: worker '{workflow_name}' missed heartbeat (>60s)"
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

