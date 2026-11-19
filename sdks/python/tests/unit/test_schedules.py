from unittest.mock import AsyncMock, MagicMock
import uuid
import httpx
import pytest

from apex_flow_sdk import ApexFlowClient, WorkflowContext


def test_workflow_decorator_registers_cron_schedule_and_validates_format():
    client = ApexFlowClient(base_url="http://test")

    @client.workflow("daily-summary", cron="  0   9 * * 1 ", timezone="America/New_York")
    async def daily_summary(ctx: WorkflowContext):
        return {"ok": True}

    assert "daily-summary" in client._workflows
    assert client._workflow_schedules["daily-summary"] == {
        "workflow_name": "daily-summary",
        "cron_expression": "0 9 * * 1",
        "timezone": "America/New_York",
    }

    with pytest.raises(ValueError, match="Invalid 5-field cron expression"):

        @client.workflow("bad-cron", cron="* * *")
        async def bad_cron_wf(ctx: WorkflowContext):
            return None


@pytest.mark.asyncio
async def test_sync_schedules_posts_declared_crons():
    client = ApexFlowClient(base_url="http://test", project_key="af_live_unit")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.raise_for_status = MagicMock()
    mock_res.json.return_value = [
        {
            "id": str(uuid.uuid4()),
            "workflow_name": "nightly-etl",
            "cron_expression": "0 2 * * *",
            "timezone": "UTC",
            "is_active": True,
        }
    ]
    client.http_client.request.return_value = mock_res

    @client.workflow("nightly-etl", cron="0 2 * * *", timezone="UTC")
    async def nightly_etl(ctx: WorkflowContext):
        return {"done": True}

    synced = await client.sync_schedules()

    assert len(synced) == 1
    assert synced[0]["workflow_name"] == "nightly-etl"
    client.http_client.request.assert_awaited_once_with(
        "POST",
        "http://test/api/v1/schedules/sync",
        json={
            "schedules": [
                {
                    "workflow_name": "nightly-etl",
                    "cron_expression": "0 2 * * *",
                    "timezone": "UTC",
                }
            ]
        },
    )


@pytest.mark.asyncio
async def test_start_worker_syncs_schedules_and_executes_dispatched_workflow():
    client = ApexFlowClient(
        base_url="http://test",
        project_key="af_live_unit",
        poll_interval_seconds=0.0,
        poll_timeout_seconds=0.0,
    )
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    run_id = uuid.uuid4()
    dispatch_step_id = uuid.uuid4()
    observed = {}

    @client.workflow("cron-report", cron="*/5 * * * *")
    async def cron_report(ctx: WorkflowContext):
        observed["run_id"] = ctx.workflow_run_id
        return {"generated": True}

    # POST sequence: heartbeat, poll (returns dispatch step)
    heartbeat_res = MagicMock(status_code=200)
    poll_res = MagicMock(status_code=200)
    poll_res.json.return_value = {
        "id": str(dispatch_step_id),
        "workflow_run_id": str(run_id),
        "step_name": "cron-report",
        "input_payload": {"trigger_source": "schedule"},
        "attempt_count": 1,
    }
    client.http_client.post.side_effect = [heartbeat_res, poll_res]

    # GET sequence: _fetch_checkpoints (optional/empty)
    checkpoints_res = MagicMock(status_code=200)
    checkpoints_res.json.return_value = {"steps": []}
    client.http_client.get.return_value = checkpoints_res

    # request sequence: sync_schedules, complete_workflow, dispatch step report
    sync_res = MagicMock(status_code=200)
    sync_res.raise_for_status = MagicMock()
    sync_res.json.return_value = [{"workflow_name": "cron-report"}]

    complete_res = MagicMock(status_code=200)
    complete_res.raise_for_status = MagicMock()

    report_res = MagicMock(status_code=200)
    client.http_client.request.side_effect = [sync_res, complete_res, report_res]

    await client.start_worker(run_once=True)

    assert observed["run_id"] == run_id
    request_calls = client.http_client.request.call_args_list
    assert request_calls[0].args == ("POST", "http://test/api/v1/schedules/sync")
    assert request_calls[1].args == ("POST", f"http://test/api/v1/workflows/{run_id}/complete")
    assert request_calls[2].args == ("POST", "http://test/api/v1/steps/report")
    assert request_calls[2].kwargs["json"]["status"] == "success"
    assert request_calls[2].kwargs["json"]["step_id"] == str(dispatch_step_id)

