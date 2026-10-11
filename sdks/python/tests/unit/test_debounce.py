import uuid
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from apex_flow_sdk import ApexFlowClient


@pytest.mark.asyncio
async def test_sdk_trigger_workflow_with_debounce():
    """Verify client.trigger_workflow passes debounce_seconds and max_debounce_seconds in creation payload."""
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    created_id = uuid.uuid4()
    mock_res = MagicMock()
    mock_res.status_code = 201
    mock_res.json.return_value = {"id": str(created_id)}
    client.http_client.request.return_value = mock_res

    res_id = await client.trigger_workflow(
        name="log_aggregator",
        deduplication_id="host_us_east_1",
        debounce_seconds=15,
        max_debounce_seconds=120,
        metadata={"batch_size": 50},
    )

    assert res_id == created_id
    call_kwargs = client.http_client.request.call_args.kwargs
    json_payload = call_kwargs["json"]
    assert json_payload["workflow_name"] == "log_aggregator"
    assert json_payload["deduplication_id"] == "host_us_east_1"
    assert json_payload["debounce_seconds"] == 15
    assert json_payload["max_debounce_seconds"] == 120
    assert json_payload["metadata"] == {"batch_size": 50}
