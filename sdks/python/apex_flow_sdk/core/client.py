import asyncio
import functools
import os
import uuid
from typing import Any, Callable, Dict, Optional
import httpx

from apex_flow_sdk.core.context import WorkflowContext


class ApexFlowClient:
    """
    Main developer client for ApexFlow SDK.
    Provides @client.workflow decorator, trigger capabilities, and worker polling loop.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        project_key: Optional[str] = None,
    ):
        resolved_url = base_url or os.getenv("APEXFLOW_BASE_URL") or "http://127.0.0.1:8000"
        self.base_url = resolved_url.rstrip("/")
        self.project_key = project_key or os.getenv("APEXFLOW_PROJECT_KEY")
        self._workflows: Dict[str, Callable] = {}

        headers = {}
        if self.project_key:
            headers["X-ApexFlow-Project-Key"] = self.project_key

        self.http_client = httpx.AsyncClient(timeout=30.0, headers=headers)



    def workflow(self, name: str):
        """Decorator to register a workflow function under a unique name."""

        def decorator(func: Callable):
            self._workflows[name] = func

            @functools.wraps(func)
            async def wrapper(ctx: WorkflowContext, *args, **kwargs):
                return await func(ctx, *args, **kwargs)

            return wrapper

        return decorator

    async def trigger_workflow(
        self,
        name: str,
        user_id: uuid.UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> uuid.UUID:
        """
        Trigger a new workflow execution run on the ApexFlow control plane.
        """
        payload = {
            "user_id": str(user_id),
            "metadata": metadata or {"workflow_name": name},
        }
        res = await self.http_client.post(f"{self.base_url}/api/v1/workflows", json=payload)
        res.raise_for_status()
        workflow_data = res.json()
        return uuid.UUID(workflow_data["id"])

    async def start_worker(self, poll_interval: float = 0.5, run_once: bool = False):
        """
        Start an asynchronous worker loop polling for queued steps from the control plane.
        """
        print(f"🚀 ApexFlow Worker started. Polling control plane at '{self.base_url}'...")
        try:
            while True:
                try:
                    res = await self.http_client.post(f"{self.base_url}/api/v1/steps/poll")
                    if res.status_code == 200 and res.json():
                        step_data = res.json()
                        step_id = step_data["id"]
                        workflow_id = uuid.UUID(step_data["workflow_id"])
                        step_name = step_data["step_name"]
                        input_payload = step_data["input_payload"]

                        print(f"⚡ Acquired step '{step_name}' (ID: {step_id})")

                        ctx = WorkflowContext(workflow_id=workflow_id, client=self)
                        ctx.step_cache[f"{step_name}_input"] = input_payload
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
