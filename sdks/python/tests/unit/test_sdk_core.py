import uuid
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_sdk_workflow_decorator_and_step_execution():
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    # Mock POST /api/v1/steps (queue step)
    mock_queue_res = MagicMock()
    mock_queue_res.status_code = 201
    mock_queue_res.json.return_value = {"id": str(uuid.uuid4())}

    # Mock POST /api/v1/steps/report (report step)
    mock_report_res = MagicMock()
    mock_report_res.status_code = 200

    client.http_client.post.side_effect = [mock_queue_res, mock_report_res]

    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    # Test executing a step
    result = await ctx.step("step-1", lambda: {"result": "success_data"})

    assert result == {"result": "success_data"}
    assert ctx.step_cache["step-1"] == {"result": "success_data"}


@pytest.mark.asyncio
async def test_sdk_step_memoization():
    client = ApexFlowClient(base_url="http://test")
    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    # Pre-seed cache
    ctx.step_cache["cached-step"] = "cached_value"

    # Execute step already in cache - should return cached value without HTTP calls
    result = await ctx.step("cached-step", lambda: "new_value")
    assert result == "cached_value"


@pytest.mark.asyncio
async def test_sdk_parallel_steps():
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    mock_queue_res = MagicMock()
    mock_queue_res.status_code = 201
    mock_queue_res.json.return_value = {"id": str(uuid.uuid4())}

    mock_report_res = MagicMock()
    mock_report_res.status_code = 200

    client.http_client.post.side_effect = [
        mock_queue_res, mock_report_res,
        mock_queue_res, mock_report_res
    ]

    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    # Test parallel steps
    results = await ctx.parallel([
        ("task-a", lambda: "res_a"),
        ("task-b", lambda: "res_b"),
    ])

    assert results == ["res_a", "res_b"]


@pytest.mark.asyncio
async def test_sdk_s3_reference_pass_through():
    """Verify that user-provided S3 URI references pass through SDK step execution cleanly without offloading errors."""
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    mock_queue_res = MagicMock()
    mock_queue_res.status_code = 201
    mock_queue_res.json.return_value = {"id": str(uuid.uuid4())}

    mock_report_res = MagicMock()
    mock_report_res.status_code = 200

    client.http_client.post.side_effect = [mock_queue_res, mock_report_res]

    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    s3_uri = "s3://my-company-bucket/dataset-2026.csv"
    step_input = {"file_url": s3_uri, "op": "process"}

    # Execute step receiving S3 reference URI input and returning S3 output URI
    result = await ctx.step(
        "s3-step",
        lambda inp: {"output_url": "s3://my-company-bucket/processed.csv"},
        input_payload=step_input,
    )

    assert result == {"output_url": "s3://my-company-bucket/processed.csv"}
    assert ctx.step_cache["s3-step"] == {"output_url": "s3://my-company-bucket/processed.csv"}


@pytest.mark.asyncio
async def test_sdk_large_payload_offload_and_resolve():
    """Verify that payloads > 250KB are offloaded via storage/upload and $apexflow_ref is created."""
    from apex_flow_sdk.adapters.storage import StorageResolver

    http_client = AsyncMock(spec=httpx.AsyncClient)
    http_client.base_url = "http://test"

    # Mock storage upload response returning reference descriptor
    ref_desc = {
        "$apexflow_ref": True,
        "key": "payloads/20261006_abc123.json",
        "size_bytes": 300000,
        "content_type": "application/json",
    }
    mock_upload_res = MagicMock()
    mock_upload_res.status_code = 200
    mock_upload_res.json.return_value = ref_desc
    http_client.post.return_value = mock_upload_res

    large_payload = {"data": "A" * 300000}
    offloaded_ref, is_offloaded = await StorageResolver.offload_if_needed(
        http_client, "http://test", large_payload
    )

    assert is_offloaded is True
    assert offloaded_ref["$apexflow_ref"] is True
    assert offloaded_ref["key"] == "payloads/20261006_abc123.json"

    # Mock storage download response for resolution
    mock_download_res = MagicMock()
    mock_download_res.status_code = 200
    mock_download_res.json.return_value = large_payload
    http_client.get.return_value = mock_download_res

    resolved = await StorageResolver.resolve_payload(http_client, "http://test", offloaded_ref)
    assert resolved == large_payload


@pytest.mark.asyncio
async def test_sdk_start_worker_long_polling_payload_and_immediate_drain():
    """Verify start_worker sends 20s timeout_seconds and re-polls immediately without interval sleep."""
    import asyncio
    import time

    # 1. run_once=True sends timeout_seconds=0.0
    client_once = ApexFlowClient(base_url="http://test")
    poll_payloads_once = []

    async def fake_post_once(url, json=None, **kwargs):
        res = MagicMock()
        if url.endswith("/api/v1/steps/poll"):
            poll_payloads_once.append(json)
            res.status_code = 204
        else:
            res.status_code = 200
        return res

    client_once.http_client = MagicMock(spec=httpx.AsyncClient)
    client_once.http_client.post = fake_post_once
    await client_once.start_worker(run_once=True)
    assert len(poll_payloads_once) == 1
    assert poll_payloads_once[0]["timeout_seconds"] == 0.0

    # 2. Continuous mode sends default 20.0s timeout and drains backlog without 5s interval sleep
    client = ApexFlowClient(base_url="http://test", poll_interval_seconds=5.0)

    @client.step("echo")
    async def echo_handler(payload):
        return {"echo": payload}

    poll_payloads = []
    poll_timestamps = []

    async def fake_post_continuous(url, json=None, **kwargs):
        res = MagicMock()
        if url.endswith("/api/v1/steps/poll"):
            poll_payloads.append(json)
            poll_timestamps.append(time.monotonic())
            if len(poll_payloads) == 1:
                res.status_code = 200
                res.json.return_value = {
                    "id": str(uuid.uuid4()),
                    "workflow_run_id": str(uuid.uuid4()),
                    "step_name": "echo",
                    "input_payload": {"msg": "hi"},
                    "attempt_count": 1,
                }
                return res
            if len(poll_payloads) == 2:
                res.status_code = 204
                return res
            raise asyncio.CancelledError()
        res.status_code = 200
        res.json.return_value = {}
        return res

    client.http_client = MagicMock(spec=httpx.AsyncClient)
    client.http_client.post = fake_post_continuous

    with pytest.raises(asyncio.CancelledError):
        await client.start_worker()

    assert len(poll_payloads) == 3
    assert all(p["timeout_seconds"] == 20.0 for p in poll_payloads)
    # Neither post-step nor post-204 re-poll waited the 5.0s poll_interval
    assert (poll_timestamps[2] - poll_timestamps[0]) < 1.0


def test_sdk_duplicate_registration_raises_value_error():
    """Verify in-memory check raises ValueError when registering duplicate workflow or step names."""
    client = ApexFlowClient(base_url="http://test")

    @client.workflow("pipeline-a")
    async def flow_one(ctx):
        pass

    with pytest.raises(ValueError, match="Workflow 'pipeline-a' is already registered"):
        @client.workflow("pipeline-a")
        async def flow_two(ctx):
            pass

    @client.step("step-alpha")
    async def step_one(payload):
        pass

    with pytest.raises(ValueError, match="Step 'step-alpha' is already registered"):
        @client.step("step-alpha")
        async def step_two(payload):
            pass

