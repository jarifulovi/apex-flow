import asyncio
import pytest
from tests.helpers.simulations import (
    SimulatedStepFunction,
    create_simulated_step,
    simulated_large_payload_step,
    simulated_retry_step,
    simulated_slow_step,
)


@pytest.mark.asyncio
async def test_simulated_step_basic_and_reset():
    step_fn = SimulatedStepFunction(return_value={"data": "test_ok"})
    assert step_fn.invocation_count == 0

    res = await step_fn()
    assert res == {"data": "test_ok"}
    assert step_fn.invocation_count == 1

    step_fn.reset()
    assert step_fn.invocation_count == 0


@pytest.mark.asyncio
async def test_simulated_step_execution_delay():
    step_fn = simulated_slow_step(delay_seconds=0.05, return_val="delayed_result")
    start = asyncio.get_event_loop().time()
    res = await step_fn()
    elapsed = asyncio.get_event_loop().time() - start

    assert res == "delayed_result"
    assert elapsed >= 0.04
    assert step_fn.invocation_count == 1


@pytest.mark.asyncio
async def test_simulated_step_fail_first_n_attempts():
    step_fn = simulated_retry_step(fail_attempts=2, exception=ValueError, error_msg="Transient DB disconnect")

    # Attempt 1 -> fails
    with pytest.raises(ValueError, match="Transient DB disconnect \\(attempt 1/2\\)"):
        await step_fn()
    assert step_fn.invocation_count == 1

    # Attempt 2 -> fails
    with pytest.raises(ValueError, match="Transient DB disconnect \\(attempt 2/2\\)"):
        await step_fn()
    assert step_fn.invocation_count == 2

    # Attempt 3 -> succeeds
    res = await step_fn()
    assert res == {"status": "success", "invocation_count": 3}
    assert step_fn.invocation_count == 3


@pytest.mark.asyncio
async def test_simulated_step_flaky_failure():
    # Flaky rate 1.0 (always fails after fail_first_n_attempts)
    step_fn = create_simulated_step(flaky_rate=1.0, error_msg="Flaky failure")
    with pytest.raises(RuntimeError, match="Flaky failure \\(flaky failure triggered\\)"):
        await step_fn()

    # Flaky rate 0.0 (never fails)
    step_fn_ok = create_simulated_step(flaky_rate=0.0)
    res = await step_fn_ok()
    assert res == {"status": "success", "invocation_count": 1}


@pytest.mark.asyncio
async def test_simulated_step_large_payload_generation():
    step_fn = simulated_large_payload_step(size_kb=300.0)
    res = await step_fn()

    assert res["simulated_large_payload"] is True
    assert res["size_kb"] == 300.0
    assert isinstance(res["dataset"], list)
    assert len(res["dataset"]) > 0


@pytest.mark.asyncio
async def test_simulated_step_callable_return_value():
    step_fn = create_simulated_step(return_val=lambda x, y: x + y)
    res = await step_fn(10, 20)
    assert res == 30
