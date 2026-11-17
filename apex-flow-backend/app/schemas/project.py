import ipaddress
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator


AlertWindowSeconds = Literal[60, 300, 900, 1800, 3600]
MaxAlertsPerWindow = Literal[1, 3, 5, 10]


def validate_webhook_url(value: str) -> str:
    """Validate and sanitize outbound webhook URLs against empty/oversized/SSRF targets."""
    cleaned = value.strip()
    if not cleaned:
        return ""
    if len(cleaned) > 512:
        raise ValueError("Webhook URL must not exceed 512 characters.")

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ("https", "http"):
        raise ValueError("Webhook URL must use http:// or https://.")
    if not parsed.hostname:
        raise ValueError("Webhook URL must contain a valid hostname.")

    host = parsed.hostname.lower().rstrip(".")
    if host in ("localhost", "0.0.0.0") or host.endswith(".local") or host.endswith(".internal"):
        raise ValueError("Webhook URL cannot target localhost or internal hostnames.")

    try:
        ip_obj = ipaddress.ip_address(host)
    except ValueError:
        return cleaned

    mapped = getattr(ip_obj, "ipv4_mapped", None)
    target_ip = mapped if mapped is not None else ip_obj
    if (
        target_ip.is_private
        or target_ip.is_loopback
        or target_ip.is_link_local
        or target_ip.is_reserved
        or target_ip.is_multicast
        or target_ip.is_unspecified
    ):
        raise ValueError("Webhook URL cannot target private, loopback, or link-local IP addresses.")

    return cleaned


class ProjectAlertSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    webhook_url: str = ""
    alert_on_failure: bool = True
    alert_on_timeout: bool = True
    alert_on_max_retry: bool = True
    alert_on_worker_disconnect: bool = False
    window_seconds: AlertWindowSeconds = 300
    max_alerts_per_window: MaxAlertsPerWindow = 3

    @field_validator("webhook_url")
    @classmethod
    def check_webhook_url(cls, value: str) -> str:
        return validate_webhook_url(value)


class ProjectCreate(BaseModel):
    name: str = "My Project"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    alerts: Optional[ProjectAlertSettings] = None


class ProjectPurgeResponse(BaseModel):
    deleted_runs: int


class WebhookTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    webhook_url: Optional[str] = None

    @field_validator("webhook_url")
    @classmethod
    def check_optional_webhook_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return validate_webhook_url(value)


class WebhookTestResponse(BaseModel):
    ok: bool
    status_code: int
    provider: str
    latency_ms: float
    detail: str


class ProjectResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    metadata: Dict[str, Any] = Field(alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProjectKeyContext(BaseModel):
    project_id: uuid.UUID
    owner_id: uuid.UUID
    key_id: uuid.UUID


class ProjectMetricsResponse(BaseModel):
    project_id: uuid.UUID
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    running_runs: int = 0
    cancelled_runs: int = 0
    success_rate_percent: float = 0.0
    active_workers_count: int = 0
    avg_duration_seconds: float = 0.0


class ActivityItemResponse(BaseModel):
    id: uuid.UUID
    workflow_id: str
    step_name: str
    status: str
    timestamp: datetime
    error_message: Optional[str] = None


class ProjectOverviewResponse(BaseModel):
    stats: ProjectMetricsResponse
    activities: List[ActivityItemResponse] = Field(default_factory=list)
    has_keys: bool = False
    has_workflows: bool = False

