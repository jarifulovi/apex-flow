import asyncio
import uuid
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_step_delay_payload_propagation():
    """Verify delay_seconds is included in step_payload when queuing a step on the control plane."""
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

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await ctx.step(
            "delayed-step",
            lambda: {"data": "processed"},
            delay_seconds=10,
        )

        assert result == {"data": "processed"}
        # Verify delay_seconds was sent in the queue payload
        first_post_call = client.http_client.post.call_args_list[0]
        payload = first_post_call.kwargs["json"]
        assert payload["step_name"] == "delayed-step"
        assert payload["delay_seconds"] == 10

        # Verify asyncio.sleep was called with delay_seconds
        mock_sleep.assert_called_with(10)


@pytest.mark.asyncio
async def test_step_without_delay_omits_delay_seconds():
    """Verify delay_seconds is omitted when not specified."""
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

    result = await ctx.step(
        "immediate-step",
        lambda: {"data": "immediate"},
    )

    assert result == {"data": "immediate"}
    first_post_call = client.http_client.post.call_args_list[0]
    payload = first_post_call.kwargs["json"]
    assert "delay_seconds" not in payload


@pytest.mark.asyncio
async def test_step_delay_skipped_on_cached_memoization():
    """Verify that cached steps return immediately without sleeping or posting."""
    client = ApexFlowClient(base_url="http://test")
    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    # Pre-seed cache
    ctx.step_cache[("cached-delayed-step", 1)] = {"cached": True}

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await ctx.step(
            "cached-delayed-step",
            lambda: {"cached": False},
            delay_seconds=15,
        )

        assert result == {"cached": True}
        mock_sleep.assert_not_called()
