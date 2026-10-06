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

