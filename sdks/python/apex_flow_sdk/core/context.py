import asyncio
import inspect
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from apex_flow_sdk.adapters.storage import StorageResolver
from apex_flow_sdk.core.encryption import (
    decrypt_if_encrypted,
    encrypt_if_key_provided,
)
from apex_flow_sdk.core.exceptions import NonRetryableError, StepFailedError


class WorkflowContext:
    """
    Workflow execution context passed into @client.workflow functions.
    Handles step queueing, durable state checkpointing, retries, and control plane reporting.
    """

    def __init__(self, workflow_run_id: uuid.UUID, client: Any, store_payloads: bool = True):
        self.workflow_run_id = workflow_run_id
        self.workflow_id = workflow_run_id  # Alias for backward compatibility
        self.client = client
        self.store_payloads = store_payloads
        self.step_cache: Dict[Any, Any] = {}
        self.completed_checkpoints: Dict[Any, Any] = {}
        self.active_step_ids: Dict[Any, str] = {}
        self._checkpoints_loaded = False
        self._step_counter = 0

    async def _fetch_checkpoints(self):
        """Fetch existing step execution checkpoints and active step IDs from the control plane."""
        if self._checkpoints_loaded:
            return
        try:
            res = await self.client.http_client.get(
                f"{self.client.base_url}/api/v1/workflows/{self.workflow_run_id}"
            )
            if res.status_code == 200:
                run_detail = res.json()
                for step_info in run_detail.get("steps", []):
                    step_name = step_info.get("step_name")
                    step_order = step_info.get("step_order")
                    status = step_info.get("status")
                    step_id = step_info.get("id")

                    if step_name and step_id:
                        if step_order is not None:
                            self.active_step_ids[(step_name, step_order)] = step_id
                        self.active_step_ids[step_name] = step_id

                    if status == "success":
                        out_payload = step_info.get("output_payload", {})
                        resolved_out = await StorageResolver.resolve_payload(
                            self.client.http_client, self.client.base_url, out_payload
                        )
                        decrypted_out = decrypt_if_encrypted(
                            resolved_out, getattr(self.client, "encryption_key", None)
                        )
                        val = decrypted_out.get("result", decrypted_out) if isinstance(decrypted_out, dict) else decrypted_out
                        if step_order is not None:
                            self.completed_checkpoints[(step_name, step_order)] = val
                        self.completed_checkpoints[step_name] = val
        except Exception:
            pass  # Fallback to local execution if checkpoint query fails
        finally:
            self._checkpoints_loaded = True

    async def step(
        self,
        name: str,
        fn: Callable[[], Any],
        retries: int = 3,
        backoff_factor: float = 2.0,
        delay_seconds: Optional[int] = None,
        priority: int = 0,
        input_payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute a modular workflow step with durable checkpointing, retries, and control plane status tracking.
        """
        self._step_counter += 1
        current_step_order = self._step_counter
        step_key = (name, current_step_order)

        # 1. Check local in-memory cache first (deterministic (name, step_order) or name for single-step fallback)
        if step_key in self.step_cache:
            return self.step_cache[step_key]
        elif name in self.step_cache and current_step_order == 1:
            return self.step_cache[name]

        # 2. Check control plane durable checkpoints (resuming from last successful step)
        await self._fetch_checkpoints()
        if step_key in self.completed_checkpoints:
            checkpoint_val = self.completed_checkpoints[step_key]
            self.step_cache[step_key] = checkpoint_val
            self.step_cache[name] = checkpoint_val
            return checkpoint_val
        elif name in self.completed_checkpoints and current_step_order == 1:
            checkpoint_val = self.completed_checkpoints[name]
            self.step_cache[step_key] = checkpoint_val
            self.step_cache[name] = checkpoint_val
            return checkpoint_val

        # 3. Use existing step ID if pre-queued or acquired, otherwise queue step on control plane
        step_id = self.active_step_ids.get(step_key)
        if not step_id and current_step_order == 1:
            step_id = self.active_step_ids.get(name)

        if not step_id:
            raw_input = input_payload or {}
            enc_input = encrypt_if_key_provided(
                raw_input, getattr(self.client, "encryption_key", None)
            )
            offloaded_input, _ = await StorageResolver.offload_if_needed(
                self.client.http_client, self.client.base_url, enc_input
            )

            step_payload = {
                "workflow_id": str(self.workflow_run_id),
                "step_name": name,
                "step_order": current_step_order,
                "input_payload": offloaded_input if isinstance(offloaded_input, dict) else {"result": offloaded_input},
                "max_attempts": retries,
            }
            if priority != 0:
                step_payload["priority"] = priority
            if delay_seconds is not None and delay_seconds > 0:
                step_payload["delay_seconds"] = delay_seconds

            res = await self.client.http_client.post(
                f"{self.client.base_url}/api/v1/steps", json=step_payload
            )
            if res.status_code not in (200, 201):
                raise StepFailedError(name, f"Failed to queue step on control plane: {res.text}")

            step_id = res.json()["id"]
            self.active_step_ids[step_key] = step_id
            self.active_step_ids[name] = step_id

        # Delay execution if initial delay requested and running inline
        if delay_seconds is not None and delay_seconds > 0:
            await asyncio.sleep(delay_seconds)

        # 4. Execute step function locally with retry logic
        last_exception: Optional[Exception] = None
        attempt = 0

        sig = inspect.signature(fn)
        has_params = len(sig.parameters) > 0
        is_async = (
            asyncio.iscoroutinefunction(fn)
            or inspect.iscoroutinefunction(fn)
            or inspect.iscoroutinefunction(getattr(fn, "__call__", None))
        )

        while attempt <= retries:
            attempt += 1
            try:
                if has_params and input_payload is not None:
                    resolved_input = await StorageResolver.resolve_payload(
                        self.client.http_client, self.client.base_url, input_payload
                    )
                    decrypted_input = decrypt_if_encrypted(
                        resolved_input, getattr(self.client, "encryption_key", None)
                    )
                    output = await fn(decrypted_input) if is_async else fn(decrypted_input)
                else:
                    output = await fn() if is_async else fn()

                if asyncio.iscoroutine(output):
                    output = await output

                # Report success to control plane
                output_data = {}
                if self.store_payloads and output is not None:
                    raw_output = output if isinstance(output, dict) else {"result": output}
                    enc_output = encrypt_if_key_provided(
                        raw_output, getattr(self.client, "encryption_key", None)
                    )
                    offloaded, _ = await StorageResolver.offload_if_needed(
                        self.client.http_client, self.client.base_url, enc_output
                    )
                    output_data = offloaded if isinstance(offloaded, dict) else {"result": offloaded}

                report_payload = {
                    "step_id": step_id,
                    "status": "success",
                    "attempt_count": attempt,
                    "output_payload": output_data,
                }
                await self.client.http_client.post(
                    f"{self.client.base_url}/api/v1/steps/report", json=report_payload
                )

                # Cache result and return
                self.step_cache[step_key] = output
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

        # 5. Report failure to control plane if all attempts exhausted
        error_msg = str(last_exception) if last_exception else "Step execution failed."
        report_payload = {
            "step_id": step_id,
            "status": "failed",
            "attempt_count": attempt,
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
        """Execute multiple independent steps concurrently."""
        tasks = [self.step(name, fn) for name, fn in steps]
        return await asyncio.gather(*tasks)

    async def child_workflow(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        deduplication_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        priority: int = 0,
    ) -> uuid.UUID:
        """
        Trigger a child sub-workflow execution run linked to this parent workflow run.
        Automatically attaches parent_workflow_id = self.workflow_run_id.
        """
        return await self.client.trigger_workflow(
            name=name,
            metadata=metadata,
            deduplication_id=deduplication_id,
            parent_workflow_id=self.workflow_run_id,
            timeout_seconds=timeout_seconds,
            priority=priority,
        )
