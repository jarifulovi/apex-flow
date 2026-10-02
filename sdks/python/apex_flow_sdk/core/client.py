import asyncio
import functools
import os
import uuid
from typing import Any, Callable, Dict, List, Optional
import httpx

from apex_flow_sdk.core.context import WorkflowContext


class ApexFlowClient:
    """
    Main developer client for ApexFlow SDK.
    Provides @client.workflow and @client.step decorators, workflow trigger capabilities,
    and targeted worker polling with durable checkpointing.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        project_key: Optional[str] = None,
        worker_name: str = "python-worker",
    ):
        resolved_url = base_url or os.getenv("APEXFLOW_BASE_URL") or "http://127.0.0.1:8000"
        self.base_url = resolved_url.rstrip("/")
        self.project_key = project_key or os.getenv("APEXFLOW_PROJECT_KEY")
        self.worker_name = worker_name
        self._workflows: Dict[str, Callable] = {}
        self._step_handlers: Dict[str, Callable] = {}

        headers = {}
        if self.project_key:
            headers["X-ApexFlow-Project-Key"] = self.project_key

        self.http_client = httpx.AsyncClient(timeout=30.0, headers=headers)

    def workflow(self, name: str):
        """Decorator to register a workflow definition under a unique name."""

        def decorator(func: Callable):
            self._workflows[name] = func

            @functools.wraps(func)
            async def wrapper(ctx: WorkflowContext, *args, **kwargs):
                return await func(ctx, *args, **kwargs)

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
    ) -> uuid.UUID:
        """
        Trigger a new workflow execution run on the ApexFlow control plane.
        """
        payload = {
            "workflow_name": name,
            "metadata": metadata or {},
        }
        res = await self.http_client.post(f"{self.base_url}/api/v1/workflows", json=payload)
        res.raise_for_status()
        workflow_data = res.json()
        return uuid.UUID(workflow_data["id"])

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
        poll_interval: float = 0.5,
        run_once: bool = False,
    ):
        """
        Start an asynchronous worker loop polling for queued steps from the control plane.
        """
        print(f"🚀 ApexFlow Worker '{self.worker_name}' started. Polling control plane at '{self.base_url}'...")
        await self.send_heartbeat()

        try:
            while True:
                try:
                    poll_payload = {
                        "step_names": step_names,
                        "worker_name": self.worker_name,
                        "lock_duration_seconds": 300,
                    }
                    res = await self.http_client.post(f"{self.base_url}/api/v1/steps/poll", json=poll_payload)
                    
                    if res.status_code == 200 and res.json():
                        step_data = res.json()
                        step_id = step_data["id"]
                        workflow_run_id = uuid.UUID(step_data["workflow_run_id"])
                        step_name = step_data["step_name"]
                        input_payload = step_data["input_payload"]

                        print(f"⚡ Acquired step '{step_name}' (ID: {step_id})")

                        # Dispatch to registered step handler or workflow definition
                        if step_name in self._step_handlers:
                            handler = self._step_handlers[step_name]
                            if asyncio.iscoroutinefunction(handler):
                                result = await handler(input_payload)
                            else:
                                result = handler(input_payload)

                            report_payload = {
                                "step_id": step_id,
                                "status": "success",
                                "output_payload": result if isinstance(result, dict) else {"result": result},
                            }
                            await self.http_client.post(f"{self.base_url}/api/v1/steps/report", json=report_payload)
                        elif self._workflows:
                            # Execute workflow context
                            ctx = WorkflowContext(workflow_run_id=workflow_run_id, client=self)
                            for wf_name, wf_func in self._workflows.items():
                                asyncio.create_task(wf_func(ctx, input_payload))

                    elif res.status_code == 204:
                        pass
                except Exception as e:
                    print(f"⚠️ Worker polling error: {e}")

                if run_once:
                    break

                await asyncio.sleep(poll_interval)
        finally:
            await self.http_client.aclose()

    async def close(self):
        """Close the underlying HTTP client."""
        await self.http_client.aclose()
