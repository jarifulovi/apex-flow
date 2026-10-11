import asyncio
import functools
import inspect
import os
import random
import signal
import sys
import uuid
from typing import Any, Callable, Dict, List, Optional, Union
import httpx

from apex_flow_sdk.adapters.storage import StorageResolver
from apex_flow_sdk.core.context import WorkflowContext


class ApexFlowClient:
    """
    Main developer client for ApexFlow SDK.
    Provides @client.workflow and @client.step decorators, workflow trigger/cancel/restart capabilities,
    and targeted worker polling with durable checkpointing and resilient retry logic.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        project_key: Optional[str] = None,
        worker_name: str = "python-worker",
        default_retries: int = 3,
        default_backoff_factor: float = 2.0,
        store_payloads: bool = True,
        poll_interval_seconds: float = 0.5,
    ):
        resolved_url = base_url or os.getenv("APEXFLOW_BASE_URL") or "http://127.0.0.1:8000"
        self.base_url = resolved_url.rstrip("/")
        self.project_key = project_key or os.getenv("APEXFLOW_PROJECT_KEY")
        self.worker_name = worker_name
        self.default_retries = default_retries
        self.default_backoff_factor = default_backoff_factor
        self.store_payloads = store_payloads
        self.poll_interval_seconds = poll_interval_seconds
        self._workflows: Dict[str, Callable] = {}
        self._step_handlers: Dict[str, Callable] = {}

        headers = {}
        if self.project_key:
            headers["X-ApexFlow-Project-Key"] = self.project_key

        self.http_client = httpx.AsyncClient(timeout=30.0, headers=headers)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        initial_delay: float = 0.5,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0,
        **kwargs,
    ) -> httpx.Response:
        """
        Execute HTTP request with exponential backoff and randomized jitter on network drops or 5xx errors.
        """
        attempt = 0
        while True:
            try:
                res = await self.http_client.request(method, url, **kwargs)
                if res.status_code in (500, 502, 503, 504) and attempt < max_retries:
                    attempt += 1
                    delay = min(max_delay, initial_delay * (backoff_factor ** (attempt - 1)))
                    jitter = random.uniform(0.75, 1.25)
                    await asyncio.sleep(delay * jitter)
                    continue
                return res
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt >= max_retries:
                    raise e
                attempt += 1
                delay = min(max_delay, initial_delay * (backoff_factor ** (attempt - 1)))
                jitter = random.uniform(0.75, 1.25)
                await asyncio.sleep(delay * jitter)

    def workflow(self, name: str):
        """Decorator to register a workflow definition under a unique name."""

        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(ctx: WorkflowContext, *args, **kwargs):
                try:
                    result = await func(ctx, *args, **kwargs)
                    await self.complete_workflow(ctx.workflow_run_id)
                    return result
                except Exception as e:
                    raise e

            self._workflows[name] = wrapper
            return wrapper

        return decorator

    def step(self, name: str):
        """Decorator to register a standalone step handler function."""

        def decorator(func: Callable):
            self._step_handlers[name] = func

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    async def trigger_workflow(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        deduplication_id: Optional[str] = None,
        parent_workflow_id: Optional[Union[str, uuid.UUID]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> uuid.UUID:
        """
        Trigger a new workflow execution run on the ApexFlow control plane.
        Supports deduplication_id for idempotency, parent_workflow_id for sub-workflows, and timeout_seconds for execution limits.
        """
        raw_metadata = metadata or {}
        offloaded_meta, _ = await StorageResolver.offload_if_needed(
            self.http_client, self.base_url, raw_metadata
        )

        payload: Dict[str, Any] = {
            "workflow_name": name,
            "metadata": offloaded_meta if isinstance(offloaded_meta, dict) else {"result": offloaded_meta},
        }
        if deduplication_id:
            payload["deduplication_id"] = deduplication_id
        if parent_workflow_id:
            payload["parent_workflow_id"] = str(parent_workflow_id)
        if timeout_seconds and timeout_seconds > 0:
            payload["timeout_seconds"] = timeout_seconds

        res = await self._request_with_retry("POST", f"{self.base_url}/api/v1/workflows", json=payload)
        res.raise_for_status()
        workflow_data = res.json()
        return uuid.UUID(workflow_data["id"])

    async def complete_workflow(self, workflow_run_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Explicitly mark workflow execution run as completed on control plane.
        """
        res = await self._request_with_retry("POST", f"{self.base_url}/api/v1/workflows/{workflow_run_id}/complete")
        res.raise_for_status()
        return res.json()

    async def cancel_workflow(self, workflow_run_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Cancel an active workflow run and mark queued steps as cancelled.
        """
        res = await self._request_with_retry("POST", f"{self.base_url}/api/v1/workflows/{workflow_run_id}/cancel")
        res.raise_for_status()
        return res.json()

    async def restart_workflow(self, workflow_run_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Reset failed or cancelled steps to queued and restart workflow run.
        """
        res = await self._request_with_retry("POST", f"{self.base_url}/api/v1/workflows/{workflow_run_id}/restart")
        res.raise_for_status()
        return res.json()

    async def send_heartbeat(self):
        """Send worker heartbeat to control plane."""
        try:
            payload = {"name": self.worker_name}
            await self.http_client.post(f"{self.base_url}/api/v1/workers/heartbeat", json=payload)
        except Exception:
            pass

    async def start_worker(
        self,
        step_names: Optional[List[str]] = None,
        poll_interval: Optional[float] = None,
        run_once: bool = False,
    ):
        """
        Start an asynchronous worker loop polling for queued steps from the control plane.
        Includes graceful signal shutdown (SIGINT / SIGTERM) and network drop auto-retry.
        """
        interval = poll_interval if poll_interval is not None else self.poll_interval_seconds
        print(f"🚀 ApexFlow Worker '{self.worker_name}' started. Polling control plane at '{self.base_url}'...")
        await self.send_heartbeat()

        stop_event = asyncio.Event()

        def _signal_handler():
            print(f"\n🛑 Worker '{self.worker_name}' received shutdown signal. Stopping polling loop...")
            stop_event.set()

        loop = asyncio.get_running_loop()
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _signal_handler)
        except (NotImplementedError, ValueError):
            pass  # Signal handlers not supported on Windows or outside main thread

        consecutive_poll_errors = 0

        try:
            while not stop_event.is_set():
                try:
                    poll_payload = {
                        "step_names": step_names,
                        "worker_name": self.worker_name,
                        "lock_duration_seconds": 300,
                    }
                    res = await self.http_client.post(f"{self.base_url}/api/v1/steps/poll", json=poll_payload)

                    if res.status_code in (200, 204):
                        consecutive_poll_errors = 0  # Reset backoff on success

                    if res.status_code == 200 and res.json():
                        step_data = res.json()
                        step_id = step_data["id"]
                        workflow_run_id = uuid.UUID(step_data["workflow_run_id"])
                        step_name = step_data["step_name"]
                        raw_input = step_data["input_payload"]

                        # Auto-resolve offloaded $apexflow_ref pointers transparently
                        input_payload = await StorageResolver.resolve_payload(
                            self.http_client, self.base_url, raw_input
                        )

                        print(f"⚡ Acquired step '{step_name}' (ID: {step_id})")

                        # Dispatch to registered step handler or workflow definition
                        if step_name in self._step_handlers:
                            handler = self._step_handlers[step_name]
                            try:
                                is_async = (
                                    asyncio.iscoroutinefunction(handler)
                                    or inspect.iscoroutinefunction(handler)
                                    or inspect.iscoroutinefunction(getattr(handler, "__call__", None))
                                )
                                if is_async:
                                    result = await handler(input_payload)
                                else:
                                    result = handler(input_payload)

                                if asyncio.iscoroutine(result):
                                    result = await result

                                output_val = result if isinstance(result, dict) else {"result": result}
                                offloaded_output, _ = await StorageResolver.offload_if_needed(
                                    self.http_client, self.base_url, output_val
                                )

                                report_payload = {
                                    "step_id": step_id,
                                    "status": "success",
                                    "output_payload": offloaded_output if isinstance(offloaded_output, dict) else {"result": offloaded_output},
                                    "attempt_count": step_data.get("attempt_count", 1),
                                }
                                await self._request_with_retry("POST", f"{self.base_url}/api/v1/steps/report", json=report_payload)
                            except Exception as step_err:
                                print(f"❌ Worker step '{step_name}' failed execution: {step_err}")
                                report_payload = {
                                    "step_id": step_id,
                                    "status": "failed",
                                    "error_message": str(step_err),
                                    "attempt_count": step_data.get("attempt_count", 1),
                                }
                                await self._request_with_retry("POST", f"{self.base_url}/api/v1/steps/report", json=report_payload)
                        elif self._workflows:
                            ctx = WorkflowContext(workflow_run_id=workflow_run_id, client=self, store_payloads=self.store_payloads)
                            for wf_name, wf_func in self._workflows.items():
                                await wf_func(ctx, input_payload)

                    elif res.status_code == 204:
                        pass
                    else:
                        consecutive_poll_errors += 1

                except Exception as e:
                    if not stop_event.is_set():
                        consecutive_poll_errors += 1
                        error_delay = min(15.0, interval * (2.0 ** min(consecutive_poll_errors, 5)))
                        jitter = random.uniform(0.8, 1.2)
                        sleep_time = error_delay * jitter
                        print(f"⚠️ Worker polling network issue ({consecutive_poll_errors}x): {e}. Retrying in {sleep_time:.1f}s...")
                        try:
                            await asyncio.wait_for(stop_event.wait(), timeout=sleep_time)
                        except asyncio.TimeoutError:
                            pass
                        continue

                if run_once or stop_event.is_set():
                    break

                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass

        finally:
            print(f"👋 Worker '{self.worker_name}' stopped cleanly.")

    async def close(self):
        """Close the underlying HTTP client."""
        await self.http_client.aclose()
