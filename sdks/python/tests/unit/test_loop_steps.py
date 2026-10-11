import uuid
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from apex_flow_sdk import ApexFlowClient, WorkflowContext


@pytest.mark.asyncio
async def test_step_execution_in_loops_is_not_falsely_memoized():
    """
    CRITICAL EDGE CASE:
    Verify that invoking ctx.step() with the SAME step_name inside a loop
    executes each iteration separately and DOES NOT return the first iteration's memoized result.
    """
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    # Mock queue step responses (returns unique ID for each queued step)
    mock_queue_responses = []
    for _ in range(5):
        m = MagicMock()
        m.status_code = 201
        m.json.return_value = {"id": str(uuid.uuid4())}
        mock_queue_responses.append(m)

    # Mock report step responses
    mock_report_res = MagicMock()
    mock_report_res.status_code = 200

    # Alternating post calls: queue, report, queue, report...
    call_responses = []
    for q in mock_queue_responses:
        call_responses.append(q)
        call_responses.append(mock_report_res)

    client.http_client.post.side_effect = call_responses

    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    items = ["item_alpha", "item_beta", "item_gamma", "item_delta", "item_omega"]
    execution_results = []
    execution_counter = 0

    for item in items:
        async def process_item_fn(val=item):
            nonlocal execution_counter
            execution_counter += 1
            return {"processed": val, "counter": execution_counter}

        # Step name is intentionally identical across all loop iterations
        res = await ctx.step("process_item", process_item_fn)
        execution_results.append(res)

    # 1. Ensure function was executed 5 distinct times (NOT once with false memoization)
    assert execution_counter == 5
    assert len(execution_results) == 5

    # 2. Ensure each iteration output matches its respective item
    for idx, item in enumerate(items):
        assert execution_results[idx]["processed"] == item
        assert execution_results[idx]["counter"] == idx + 1

    # 3. Verify that the cache holds independent entries for each (name, step_order)
    assert ctx.step_cache[("process_item", 1)]["processed"] == "item_alpha"
    assert ctx.step_cache[("process_item", 2)]["processed"] == "item_beta"
    assert ctx.step_cache[("process_item", 3)]["processed"] == "item_gamma"
    assert ctx.step_cache[("process_item", 4)]["processed"] == "item_delta"
    assert ctx.step_cache[("process_item", 5)]["processed"] == "item_omega"


@pytest.mark.asyncio
async def test_loop_steps_durable_checkpoint_resumption():
    """
    Verify that if steps 1 and 2 of a loop completed in a prior run,
    re-running the workflow skips steps 1 and 2 and resumes execution at step 3.
    """
    client = ApexFlowClient(base_url="http://test")
    client.http_client = AsyncMock(spec=httpx.AsyncClient)

    workflow_id = uuid.uuid4()
    ctx = WorkflowContext(workflow_run_id=workflow_id, client=client)

    # Simulate control plane returning 2 already completed steps for "batch_chunk"
    mock_get_wf_res = MagicMock()
    mock_get_wf_res.status_code = 200
    mock_get_wf_res.json.return_value = {
        "id": str(workflow_id),
        "status": "running",
        "steps": [
            {
                "id": str(uuid.uuid4()),
                "step_name": "batch_chunk",
                "step_order": 1,
                "status": "success",
                "output_payload": {"result": "memoized_chunk_1"},
            },
            {
                "id": str(uuid.uuid4()),
                "step_name": "batch_chunk",
                "step_order": 2,
                "status": "success",
                "output_payload": {"result": "memoized_chunk_2"},
            },
        ],
    }
    client.http_client.get.return_value = mock_get_wf_res

    # Mock queue and report for step 3 (which will execute)
    mock_queue_res = MagicMock()
    mock_queue_res.status_code = 201
    mock_queue_res.json.return_value = {"id": str(uuid.uuid4())}

    mock_report_res = MagicMock()
    mock_report_res.status_code = 200

    client.http_client.post.side_effect = [mock_queue_res, mock_report_res]

    executed_chunks = []

    # Run loop over 3 chunks
    for i in range(1, 4):
        chunk_num = i
        async def run_chunk():
            executed_chunks.append(chunk_num)
            return f"fresh_chunk_{chunk_num}"

        res = await ctx.step("batch_chunk", run_chunk)
        if i == 1:
            assert res == "memoized_chunk_1"
        elif i == 2:
            assert res == "memoized_chunk_2"
        elif i == 3:
            assert res == "fresh_chunk_3"

    # Only chunk 3 should have actually run! Chunks 1 and 2 were restored from checkpoints
    assert executed_chunks == [3]
