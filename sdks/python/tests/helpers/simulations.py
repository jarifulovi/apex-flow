import asyncio
import random
from typing import Any, Callable, Dict, Optional, Type, Union


class SimulatedStepFunction:
    """
    Configurable step function simulator for E2E testing.
    Merges multiple runtime behavior properties into a single flexible instance:
    - execution_delay_seconds: Artificial delay simulating slow I/O or heavy computation.
    - fail_first_n_attempts: Fails the first N invocations and succeeds on subsequent attempts.
    - error_exception_class: Custom exception class raised during simulated failures.
    - flaky_failure_rate: Random failure probability (0.0 to 1.0).
    - return_value: Custom payload returned upon success.
    - large_payload_kb: Generates a large dict payload of ~N KB upon success to test offloading.
    """

    def __init__(
        self,
        execution_delay_seconds: float = 0.0,
        fail_first_n_attempts: int = 0,
        error_exception_class: Type[Exception] = RuntimeError,
        error_message: str = "Simulated step execution failure",
        flaky_failure_rate: Optional[float] = None,
        return_value: Any = None,
        large_payload_kb: Optional[float] = None,
    ):
        self.execution_delay_seconds = execution_delay_seconds
        self.fail_first_n_attempts = fail_first_n_attempts
        self.error_exception_class = error_exception_class
        self.error_message = error_message
        self.flaky_failure_rate = flaky_failure_rate
        self.return_value = return_value
        self.large_payload_kb = large_payload_kb
        self.invocation_count = 0

    async def __call__(self, *args, **kwargs) -> Any:
        self.invocation_count += 1

        # 1. Simulate artificial execution delay
        if self.execution_delay_seconds > 0:
            await asyncio.sleep(self.execution_delay_seconds)

        # 2. Simulate failure for the first N attempts
        if self.invocation_count <= self.fail_first_n_attempts:
            raise self.error_exception_class(
                f"{self.error_message} (attempt {self.invocation_count}/{self.fail_first_n_attempts})"
            )

        # 3. Simulate probabilistic flakiness
        if self.flaky_failure_rate is not None and random.random() < self.flaky_failure_rate:
            raise self.error_exception_class(f"{self.error_message} (flaky failure triggered)")

        # 4. Return custom value or generated large payload
        if self.large_payload_kb is not None:
            repeat_count = max(1, int((self.large_payload_kb * 1024) // 100))
            return {
                "simulated_large_payload": True,
                "size_kb": self.large_payload_kb,
                "dataset": ["ApexFlow_simulated_payload_token_" * 4 for _ in range(repeat_count)],
            }

        if self.return_value is not None:
            if callable(self.return_value):
                return self.return_value(*args, **kwargs)
            return self.return_value

        return {"status": "success", "invocation_count": self.invocation_count}

    def reset(self):
        """Reset invocation counter."""
        self.invocation_count = 0


def create_simulated_step(
    delay: float = 0.0,
    fail_attempts: int = 0,
    exception: Type[Exception] = RuntimeError,
    error_msg: str = "Simulated step error",
    flaky_rate: Optional[float] = None,
    return_val: Any = None,
    large_payload_kb: Optional[float] = None,
) -> SimulatedStepFunction:
    """Convenience factory function for SimulatedStepFunction."""
    return SimulatedStepFunction(
        execution_delay_seconds=delay,
        fail_first_n_attempts=fail_attempts,
        error_exception_class=exception,
        error_message=error_msg,
        flaky_failure_rate=flaky_rate,
        return_value=return_val,
        large_payload_kb=large_payload_kb,
    )


def simulated_slow_step(delay_seconds: float = 0.1, return_val: Any = None) -> SimulatedStepFunction:
    """Shortcut factory for slow I/O / heavy computation step."""
    return create_simulated_step(delay=delay_seconds, return_val=return_val)


def simulated_retry_step(fail_attempts: int = 2, exception: Type[Exception] = RuntimeError, error_msg: str = "Transient step error") -> SimulatedStepFunction:
    """Shortcut factory for transient failure step requiring retries."""
    return create_simulated_step(fail_attempts=fail_attempts, exception=exception, error_msg=error_msg)


def simulated_large_payload_step(size_kb: float = 450.0) -> SimulatedStepFunction:
    """Shortcut factory for large payload offloading step (>250KB)."""
    return create_simulated_step(large_payload_kb=size_kb)
