import asyncio
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from apex_flow_sdk.core.exceptions import NonRetryableError, StepFailedError


class WorkflowContext:
    """
    Workflow execution context passed into @client.workflow functions.
    Handles step queueing, state memoization, local retries, and control plane reporting.
    """

    def __init__(self, workflow_id: uuid.UUID, client: Any):
        self.workflow_id = workflow_id
        self.client = client
        self.step_cache: Dict[str, Any] = {}

    async def step(
        self,
        name: str,
        fn: Callable[[], Any],
        retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> Any:
        """
        Execute a modular workflow step durable with retries & control plane state tracking.
        """
        # 1. Check if step output is already cached/memoized locally
        if name in self.step_cache:
            return self.step_cache[name]

        # 2. Queue step on control plane
        step_payload = {
            "workflow_id": str(self.workflow_id),
            "step_name": name,
            "input_payload": {},
        }
        res = await self.client.http_client.post(
            f"{self.client.base_url}/api/v1/steps", json=step_payload
        )
        if res.status_code != 201:
            raise StepFailedError(name, f"Failed to queue step on control plane: {res.text}")

        step_id = res.json()["id"]

        # 3. Execute step locally with retry loop
        last_exception: Optional[Exception] = None
        attempt = 0

        while attempt <= retries:
            attempt += 1
            try:
                # Call local step function
                if asyncio.iscoroutinefunction(fn):
                    output = await fn()
                else:
                    output = fn()

                # Report success to control plane
                report_payload = {
                    "step_id": step_id,
                    "status": "success",
                    "output_payload": output if isinstance(output, dict) else {"result": output},
                }
                await self.client.http_client.post(
                    f"{self.client.base_url}/api/v1/steps/report", json=report_payload
                )

                # Cache output in memory and return
                self.step_cache[name] = output
                return output

            except NonRetryableError as e:
                last_exception = e
                break
            except Exception as e:
                last_exception = e
                if attempt <= retries:
                    sleep_time = backoff_factor ** (attempt - 1)
                    await asyncio.sleep(sleep_time)

        # 4. Report failure to control plane if all retries exhausted
        error_msg = str(last_exception) if last_exception else "Step execution failed."
        report_payload = {
            "step_id": step_id,
            "status": "failed",
            "error_message": error_msg,
        }
        await self.client.http_client.post(
            f"{self.client.base_url}/api/v1/steps/report", json=report_payload
        )
        raise StepFailedError(name, error_msg, original_error=last_exception)

    async def parallel(
        self,
        steps: List[Tuple[str, Callable[[], Any]]],
    ) -> List[Any]:
        """
        Execute multiple independent steps concurrently using asyncio.gather.
        """
        tasks = [self.step(name, fn) for name, fn in steps]
        return await asyncio.gather(*tasks)
