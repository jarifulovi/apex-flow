import uuid
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_trigger_workflow_propagates_timeout_seconds():
    """Verify trigger_workflow sends timeout_seconds in POST payload."""
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    created_id = uuid.uuid4()
    mock_res = MagicMock()
    mock_res.status_code = 201
    mock_res.json.return_value = {"id": str(created_id)}
    client.http_client.request.return_value = mock_res

    res_id = await client.trigger_workflow(
        name="timed_workflow",
        timeout_seconds=300,
    )

    assert res_id == created_id
    call_kwargs = client.http_client.request.call_args.kwargs
    assert call_kwargs["json"]["workflow_name"] == "timed_workflow"
    assert call_kwargs["json"]["timeout_seconds"] == 300


@pytest.mark.asyncio
async def test_child_workflow_propagates_timeout_seconds():
    """Verify ctx.child_workflow sends parent_workflow_id and timeout_seconds."""
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    child_id = uuid.uuid4()
    mock_res = MagicMock()
    mock_res.status_code = 201
    mock_res.json.return_value = {"id": str(child_id)}
    client.http_client.request.return_value = mock_res

    parent_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=parent_id, client=client)

    res_id = await ctx.child_workflow(
        name="sub_pipeline",
        timeout_seconds=60,
    )

    assert res_id == child_id
    call_kwargs = client.http_client.request.call_args.kwargs
    payload = call_kwargs["json"]
    assert payload["workflow_name"] == "sub_pipeline"
    assert payload["parent_workflow_id"] == str(parent_id)
    assert payload["timeout_seconds"] == 60


@pytest.mark.asyncio
async def test_step_propagates_priority():
    """Verify ctx.step sends priority in step_payload when non-zero."""
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    mock_queue_res = MagicMock()
    mock_queue_res.status_code = 201
    mock_queue_res.json.return_value = {"id": str(uuid.uuid4())}

    mock_report_res = MagicMock()
    mock_report_res.status_code = 200

    client.http_client.post.side_effect = [mock_queue_res, mock_report_res]

    ctx = WorkflowContext(workflow_run_id=uuid.uuid4(), client=client)

    result = await ctx.step(
        "high_priority_step",
        lambda: "urgent_done",
        priority=-5,
    )

    assert result == "urgent_done"
    first_post_call = client.http_client.post.call_args_list[0]
    payload = first_post_call.kwargs["json"]
    assert payload["step_name"] == "high_priority_step"
    assert payload["priority"] == -5
