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
    ctx = WorkflowContext(workflow_id=workflow_id, client=client)

    # Test executing a step
    result = await ctx.step("step-1", lambda: {"result": "success_data"})

    assert result == {"result": "success_data"}
    assert ctx.step_cache["step-1"] == {"result": "success_data"}


@pytest.mark.asyncio
async def test_sdk_step_memoization():
    client = ApexFlowClient(base_url="http://test")
    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_id=workflow_id, client=client)

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
    ctx = WorkflowContext(workflow_id=workflow_id, client=client)

    # Test parallel steps
    results = await ctx.parallel([
        ("task-a", lambda: "res_a"),
        ("task-b", lambda: "res_b"),
    ])

    assert results == ["res_a", "res_b"]
