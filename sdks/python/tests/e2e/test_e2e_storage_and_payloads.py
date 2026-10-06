import asyncio
import uuid
import pytest
from apex_flow_sdk import ApexFlowClient, WorkflowContext
from apex_flow_sdk.adapters.storage import StorageResolver
from tests.helpers.assertions import ApexFlowAssert


@pytest.mark.asyncio
async def test_large_payload_offloading_and_descriptor_creation(test_client_harness: ApexFlowClient):
    """
    Test large payload (>250KB) offloading engine:
    1. Step generates large output (>250KB).
    2. Control plane DB records an $apexflow_ref descriptor for step output.
    3. ApexFlowAssert validates descriptor fields.
    """
    client = test_client_harness

    run_id = await client.trigger_workflow("large-payload-offload-pipeline")
    assert isinstance(run_id, uuid.UUID)

    # Queue step under run
    q_res = await client.http_client.post(
        "/api/v1/steps",
        json={"workflow_id": str(run_id), "step_name": "generate_large_output", "step_order": 1},
    )
    assert q_res.status_code in (200, 201)

    # Define step handler generating ~450KB dataset (>250KB threshold)
    large_records = [{"id": i, "chunk": "ApexFlow offloading validation token " * 20} for i in range(600)]
    large_output = {"dataset": large_records, "total_records": 600}

    @client.step("generate_large_output")
    async def step_handler(payload):
        return large_output

    # Run worker to process step
    await client.start_worker(step_names=["generate_large_output"], poll_interval=0.01, run_once=True)

    # Inspect workflow run state from control plane
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()

    steps = {s["step_name"]: s for s in wf_data["steps"]}
    assert "generate_large_output" in steps

    step_output = steps["generate_large_output"]["output_payload"]
    ApexFlowAssert.assert_ref_descriptor(step_output, min_size=250000, expected_content_type="application/json")

    # Resolve $apexflow_ref descriptor back into native object
    resolved_meta = await StorageResolver.resolve_payload(
        client.http_client, client.base_url, step_output
    )
    assert isinstance(resolved_meta, dict)
    assert resolved_meta["total_records"] == 600
    assert len(resolved_meta["dataset"]) == 600


@pytest.mark.asyncio
async def test_binary_stream_payload_offloading(test_client_harness: ApexFlowClient):
    """
    Test raw binary bytes payload offloading (>250KB).
    """
    client = test_client_harness

    # Generate 300KB raw byte stream
    binary_data = b"APEXFLOW_BINARY_CHUNK_DATA_" * 11000  # ~300KB

    offloaded_ref, was_offloaded = await StorageResolver.offload_if_needed(
        client.http_client, client.base_url, binary_data
    )

    assert was_offloaded is True
    ApexFlowAssert.assert_ref_descriptor(offloaded_ref, min_size=250000, expected_content_type="application/octet-stream")

    # Download & dereference back to bytes
    restored_bytes = await StorageResolver.resolve_payload(
        client.http_client, client.base_url, offloaded_ref
    )
    assert isinstance(restored_bytes, bytes)
    assert len(restored_bytes) == len(binary_data)
    assert restored_bytes == binary_data


@pytest.mark.asyncio
async def test_inline_payload_pass_through(test_client_harness: ApexFlowClient):
    """
    Test that small payloads (<= 250KB) remain inline in PostgreSQL jsonb without offloading.
    """
    client = test_client_harness

    small_payload = {"user_id": 101, "role": "admin", "tags": ["fast", "inline"]}

    offloaded_ref, was_offloaded = await StorageResolver.offload_if_needed(
        client.http_client, client.base_url, small_payload
    )

    assert was_offloaded is False
    assert offloaded_ref == small_payload
    assert StorageResolver.is_ref(offloaded_ref) is False


@pytest.mark.asyncio
async def test_explicit_step_input_payload_offloading_and_resolution(test_client_harness: ApexFlowClient):
    """
    Test explicit input_payload offloading in ctx.step(..., input_payload=large_dict):
    1. Large input_payload (>250KB) passed to ctx.step().
    2. Input payload is offloaded to $apexflow_ref descriptor before queuing.
    3. Step handler function receives dereferenced native dict.
    """
    client = test_client_harness

    run_id = await client.trigger_workflow("explicit-input-offload-pipeline")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)

    large_input = {"dataset": ["row_" + str(i) + "_ApexFlow_offload_token_" * 30 for i in range(800)]}

    received_input = None

    async def consume_large_input(payload):
        nonlocal received_input
        received_input = payload
        return {"processed_rows": len(payload["dataset"])}

    res = await ctx.step("process-offloaded-input", consume_large_input, input_payload=large_input)
    assert res["processed_rows"] == 800
    assert received_input is not None
    assert len(received_input["dataset"]) == 800

    # Inspect DB state to verify input_payload stored as $apexflow_ref
    wf_res = await client.http_client.get(f"/api/v1/workflows/{run_id}")
    assert wf_res.status_code == 200
    wf_data = wf_res.json()

    step_data = [s for s in wf_data["steps"] if s["step_name"] == "process-offloaded-input"][0]
    ApexFlowAssert.assert_ref_descriptor(step_data["input_payload"], min_size=250000)

