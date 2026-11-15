import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import httpx
import pytest
from pydantic import ValidationError

from app.models.project import Project
from app.schemas.project import (
    ProjectAlertSettings,
    ProjectUpdate,
    WebhookTestRequest,
)
from app.services.alerts.alert_service import (
    AlertFormatter,
    AlertService,
    SlidingWindowLimiter,
    detect_webhook_provider,
)
from app.services.projects.project_service import ProjectService


def test_alert_settings_schema_accepts_valid_presets_and_urls():
    valid_slack = ProjectAlertSettings(
        webhook_url="https://hooks.slack.com/services/T123/B456/secret",
        alert_on_failure=True,
        alert_on_timeout=True,
        alert_on_max_retry=False,
        window_seconds=300,
        max_alerts_per_window=3,
    )
    assert valid_slack.window_seconds == 300
    assert valid_slack.max_alerts_per_window == 3

    empty_disabled = ProjectAlertSettings(webhook_url="   ")
    assert empty_disabled.webhook_url == ""


def test_alert_settings_schema_rejects_invalid_presets_and_extra_fields():
    # Out-of-set window_seconds
    with pytest.raises(ValidationError):
        ProjectAlertSettings(window_seconds=45)  # type: ignore[arg-type]

    # Out-of-set max_alerts_per_window
    with pytest.raises(ValidationError):
        ProjectAlertSettings(max_alerts_per_window=7)  # type: ignore[arg-type]

    # Extra unknown or removed fields forbidden on ProjectUpdate
    with pytest.raises(ValidationError):
        ProjectAlertSettings(unknown_field="nope")  # type: ignore[call-arg]

    for removed_field in ("environment", "region", "description", "execution", "retention", "extra_key"):
        with pytest.raises(ValidationError):
            ProjectUpdate(**{removed_field: "forbidden"})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1:8000/hook",
        "https://localhost/webhook",
        "https://169.254.169.254/latest/meta-data",
        "https://10.0.0.5/internal",
        "https://192.168.1.50/hook",
        "http://[::1]/hook",
        "http://service.internal/alert",
        "ftp://hooks.slack.com/services/T1/B2/C3",
        "https://example.com/" + ("a" * 520),
    ],
)
def test_webhook_url_ssrf_and_scheme_validation_rejects_unsafe_urls(bad_url: str):
    with pytest.raises(ValidationError):
        ProjectAlertSettings(webhook_url=bad_url)

    with pytest.raises(ValidationError):
        WebhookTestRequest(webhook_url=bad_url)


def test_detect_webhook_provider_and_formatters():
    slack_url = "https://hooks.slack.com/services/T000/B000/XYZ"
    discord_url = "https://discord.com/api/webhooks/123456/abcdef"
    legacy_discord_url = "https://discordapp.com/api/webhooks/123456/abcdef"
    generic_url = "https://alerts.example.com/webhooks/apexflow"

    assert detect_webhook_provider(slack_url) == "slack"
    assert detect_webhook_provider(discord_url) == "discord"
    assert detect_webhook_provider(legacy_discord_url) == "discord"
    assert detect_webhook_provider(generic_url) == "webhook"

    project_id = uuid.uuid4()
    run_id = uuid.uuid4()

    slack_payload = AlertFormatter.format_event_payload(
        provider="slack",
        event_type="step.max_retries_exhausted",
        project_id=project_id,
        project_name="Prod App",
        workflow_name="billing_sync",
        workflow_run_id=run_id,
        step_name="charge_card",
        attempt_count=3,
        max_attempts=3,
        error_message="Gateway 502",
    )
    assert "blocks" in slack_payload
    assert "billing_sync" in slack_payload["text"]
    assert slack_payload["blocks"][0]["type"] == "header"

    discord_payload = AlertFormatter.format_event_payload(
        provider="discord",
        event_type="workflow.timed_out",
        project_id=project_id,
        project_name="Prod App",
        workflow_name="video_render",
        workflow_run_id=run_id,
        error_message="Exceeded 60s timeout",
    )
    assert "embeds" in discord_payload
    assert discord_payload["embeds"][0]["color"] == 0xF59E0B
    assert discord_payload["embeds"][0]["title"] == "Workflow Execution Timed Out"

    generic_payload = AlertFormatter.format_event_payload(
        provider="webhook",
        event_type="alert.digest",
        project_id=project_id,
        project_name="Prod App",
        workflow_name="billing_sync",
        suppressed_count=12,
        window_seconds=300,
    )
    assert generic_payload["event"] == "alert.digest"
    assert generic_payload["suppressed_count"] == 12
    assert generic_payload["workflow_name"] == "billing_sync"


def test_sliding_window_per_workflow_isolation_and_project_ceiling():
    limiter = SlidingWindowLimiter()
    project_id = uuid.uuid4()
    run_id = uuid.uuid4()

    # max_alerts_per_window = 2 => per-workflow limit 2, project ceiling = 6
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_alpha",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=100.0,
    ) is True
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_alpha",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=105.0,
    ) is True
    # 3rd alert for wf_alpha is throttled and enters digest
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_alpha",
        window_seconds=60,
        max_alerts_per_window=2,
        error_message="alpha err 3",
        workflow_run_id=run_id,
        now_mono=110.0,
    ) is False

    bucket = limiter.pop_digest(project_id, "wf_alpha")
    assert bucket is not None
    assert bucket.count == 1
    assert bucket.latest_error == "alpha err 3"
    assert bucket.latest_run_id == run_id

    # Separate workflows are NOT blocked because wf_alpha hit its own cap
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_beta",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=111.0,
    ) is True
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_beta",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=112.0,
    ) is True
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_gamma",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=113.0,
    ) is True
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_gamma",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=114.0,
    ) is True

    # Project-wide total is now 6 (2*3 == 6), so even a brand new workflow hits project ceiling
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_delta",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=115.0,
    ) is False

    # Once earliest timestamps age out (> 100.0 + 60.0), new alert succeeds
    assert limiter.check_and_record(
        project_id=project_id,
        workflow_name="wf_alpha",
        window_seconds=60,
        max_alerts_per_window=2,
        now_mono=166.0,
    ) is True


@pytest.mark.asyncio
async def test_sliding_window_digest_flushes_after_expiry():
    limiter = SlidingWindowLimiter()
    project_id = uuid.uuid4()
    flushed_buckets: List[Any] = []

    async def on_flush(bucket: Any) -> None:
        flushed_buckets.append(bucket)

    # First fill 1 slot with a 0.12s window
    now = 1000.0
    with patch("app.services.alerts.alert_service.time.monotonic", return_value=now):
        allowed1 = limiter.check_and_record(
            project_id=project_id,
            workflow_name="wf_storm",
            window_seconds=1,
            max_alerts_per_window=1,
            project_name="Storm Proj",
            webhook_url="https://example.com/hook",
            now_mono=now,
            on_flush=on_flush,
        )
        assert allowed1 is True

        # Trigger throttling slightly before window expires (~0.1s remaining)
        allowed2 = limiter.check_and_record(
            project_id=project_id,
            workflow_name="wf_storm",
            window_seconds=1,
            max_alerts_per_window=1,
            project_name="Storm Proj",
            webhook_url="https://example.com/hook",
            error_message="Err A",
            now_mono=now + 0.90,
            on_flush=on_flush,
        )
        allowed3 = limiter.check_and_record(
            project_id=project_id,
            workflow_name="wf_storm",
            window_seconds=1,
            max_alerts_per_window=1,
            project_name="Storm Proj",
            webhook_url="https://example.com/hook",
            error_message="Err B",
            now_mono=now + 0.92,
            on_flush=on_flush,
        )
        assert allowed2 is False
        assert allowed3 is False

    await asyncio.sleep(0.25)
    assert len(flushed_buckets) == 1
    assert flushed_buckets[0].count == 2
    assert flushed_buckets[0].latest_error == "Err B"
    limiter.reset()


@pytest.mark.asyncio
async def test_alert_service_emit_and_test_webhook():
    AlertService.get_limiter().reset()
    project = Project(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Checkout Service",
        metadata_={
            "alerts": {
                "webhook_url": "https://discord.com/api/webhooks/111/222",
                "alert_on_failure": True,
                "alert_on_timeout": False,
                "alert_on_max_retry": True,
                "window_seconds": 300,
                "max_alerts_per_window": 3,
            }
        },
    )

    recorded_posts: List[Dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_posts.append({"url": str(request.url), "content": request.read()})
        return httpx.Response(204, text="")

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def client_factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    with patch("app.services.alerts.alert_service.httpx.AsyncClient", side_effect=client_factory):
        test_res = await AlertService.send_test_alert(project=project)
        assert test_res.ok is True
        assert test_res.status_code == 204
        assert test_res.provider == "discord"

        # Test alert should NOT consume sliding window capacity for failures
        emitted_failure = await AlertService.emit_alert(
            project=project,
            event_type="step.max_retries_exhausted",
            workflow_run_id=uuid.uuid4(),
            workflow_name="checkout_flow",
            step_name="reserve_inventory",
            attempt_count=3,
            max_attempts=3,
            error_message="Stock unavailable",
        )
        assert emitted_failure is True

        # Timeout alert disabled because alert_on_timeout=False and timeout uses alert_on_timeout or alert_on_failure?
        # Note: workflow.timed_out checks (alert_on_timeout or alert_on_failure); disable both to verify gating.
        project.metadata_["alerts"]["alert_on_failure"] = False
        skipped_timeout = await AlertService.emit_alert(
            project=project,
            event_type="workflow.timed_out",
            workflow_run_id=uuid.uuid4(),
            workflow_name="checkout_flow",
        )
        assert skipped_timeout is False

    assert len(recorded_posts) == 2
    AlertService.get_limiter().reset()


@pytest.mark.asyncio
async def test_project_service_update_project_persists_strict_metadata():
    owner_id = uuid.uuid4()
    project = Project(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Default Project",
        metadata_={"is_default": True},
    )

    db = AsyncMock()
    db.refresh = AsyncMock()
    get_res = MagicMock()
    get_res.scalar_one_or_none.return_value = project

    dup_res = MagicMock()
    dup_res.scalar_one_or_none.return_value = None

    db.execute.side_effect = [get_res, dup_res]

    payload = ProjectUpdate(
        name="Production Pipeline",
        alerts=ProjectAlertSettings(
            webhook_url="https://hooks.slack.com/services/T1/B2/C3",
            alert_on_failure=True,
            alert_on_timeout=True,
            alert_on_max_retry=True,
            window_seconds=900,
            max_alerts_per_window=5,
        ),
    )

    updated = await ProjectService.update_project(
        db=db, project_id=project.id, owner_id=owner_id, payload=payload
    )

    assert updated.name == "Production Pipeline"
    assert updated.metadata_["is_default"] is True
    assert updated.metadata_["alerts"]["window_seconds"] == 900
    assert updated.metadata_["alerts"]["max_alerts_per_window"] == 5
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_project_service_purge_project_logs_deletes_finished_runs():
    owner_id = uuid.uuid4()
    project = Project(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Test Project",
        metadata_={},
    )

    db = AsyncMock()
    get_res = MagicMock()
    get_res.scalar_one_or_none.return_value = project

    del_res = MagicMock()
    del_res.rowcount = 14

    db.execute.side_effect = [get_res, del_res]

    deleted_count = await ProjectService.purge_project_logs(
        db=db, project_id=project.id, owner_id=owner_id
    )

    assert deleted_count == 14
    assert db.execute.call_count == 2
    db.commit.assert_called_once()

