import uuid
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_sdk_fork_workflow_payload():
    """Verify client.fork_workflow sends proper request payload to the control plane."""
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    forked_id = uuid.uuid4()
    mock_res = MagicMock()
    mock_res.status_code = 201
    mock_res.json.return_value = {"id": str(forked_id)}
    client.http_client.request.return_value = mock_res

    source_id = uuid.uuid4()
    res_id = await client.fork_workflow(
        workflow_run_id=source_id,
        from_step_order=3,
        workflow_name="forked_test_run",
        metadata_override={"branch": "hotfix"},
        priority=-10,
    )

    assert res_id == forked_id
    call_args = client.http_client.request.call_args
    assert call_args.args[0] == "POST"
    assert call_args.args[1] == f"http://test/api/v1/workflows/{source_id}/fork"
    payload = call_args.kwargs["json"]
    assert payload["from_step_order"] == 3
    assert payload["workflow_name"] == "forked_test_run"
    assert payload["metadata_override"] == {"branch": "hotfix"}
    assert payload["priority"] == -10


@pytest.mark.asyncio
async def test_sdk_trigger_workflow_with_priority():
    """Verify client.trigger_workflow passes priority in creation payload."""
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    created_id = uuid.uuid4()
    mock_res = MagicMock()
    mock_res.status_code = 201
    mock_res.json.return_value = {"id": str(created_id)}
    client.http_client.request.return_value = mock_res

    res_id = await client.trigger_workflow(
        name="priority_pipeline",
        priority=-20,
    )

    assert res_id == created_id
    call_kwargs = client.http_client.request.call_args.kwargs
    assert call_kwargs["json"]["priority"] == -20


@pytest.mark.asyncio
async def test_sdk_step_with_custom_priority():
    """Verify ctx.step propagates non-zero priority in step_payload."""
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
        "custom_priority_step",
        lambda: {"status": "ok"},
        priority=5,
    )

    assert result == {"status": "ok"}
    first_post_call = client.http_client.post.call_args_list[0]
    payload = first_post_call.kwargs["json"]
    assert payload["priority"] == 5
