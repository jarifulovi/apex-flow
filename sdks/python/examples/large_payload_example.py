import asyncio
import os
import sys
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add SDK root to path for local development
SDK_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SDK_ROOT))

from apex_flow_sdk import ApexFlowClient, WorkflowContext


client = ApexFlowClient(
    base_url=os.getenv("APEXFLOW_BASE_URL", "http://127.0.0.1:8000"),
    project_key=os.getenv("APEXFLOW_PROJECT_KEY"),
    worker_name="large-payload-worker",
)


@client.workflow("large_payload_pipeline")
async def large_payload_pipeline(ctx: WorkflowContext, input_data: dict):
    print("📦 [Workflow] Starting Large Payload Offloading Pipeline...")

    # Step 1: Generate >250KB dataset
    async def generate_dataset():
        print("  ⚡ [Step 1] Generating ~500KB dataset...")
        # Create 500KB json payload
        chunk = "ApexFlow durable state offloading engine validation token " * 100
        items = [{"id": i, "data": chunk} for i in range(120)]
        return {"total_records": len(items), "records": items}

    dataset = await ctx.step(
        "generate_large_dataset",
        generate_dataset,
        input_payload={"target_size": "~500KB", "records_requested": 120},
    )
    print(f"  ✅ [Step 1 Completed] Generated dataset with {dataset.get('total_records')} records.")

    # Step 2: Transform and process the dataset
    async def transform_dataset():
        print("  ⚡ [Step 2] Processing dataset records...")
        records = dataset.get("records", [])
        total_len = sum(len(r["data"]) for r in records)
        return {
            "status": "PROCESSED",
            "records_processed": len(records),
            "total_bytes_processed": total_len,
            "sample": records[0] if records else None,
        }

    result = await ctx.step(
        "process_dataset",
        transform_dataset,
        input_payload={"stage": "transformation", "records_to_process": len(dataset.get("records", []))},
    )
    print(f"  ✅ [Step 2 Completed] Total bytes processed: {result.get('total_bytes_processed')}")
    return result


async def main():
    print("=========================================================")
    print("📦 ApexFlow Milestone 5: Large Payload Offloading Demo")
    print("=========================================================")

    # 1. Trigger workflow run
    print("1️⃣ Triggering 'large_payload_pipeline' workflow run...")
    run_id = await client.trigger_workflow(
        name="large_payload_pipeline",
        metadata={"environment": "production", "demo": "milestone_5"},
    )
    print(f"  ✅ Triggered Workflow Run ID: {run_id}")

    # 2. Execute Workflow Pipeline locally with durable checkpointing
    print("\n2️⃣ Executing workflow pipeline with durable state context...")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)
    result = await large_payload_pipeline(ctx, {"demo": True})

    # 3. Inspect control plane state to verify offloading
    print("\n3️⃣ Inspecting control plane DB state for $apexflow_ref descriptors...")
    headers = {"X-ApexFlow-Project-Key": client.project_key} if client.project_key else {}
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as http:
        run_res = await http.get(f"{client.base_url}/api/v1/workflows/{run_id}")
        run_res.raise_for_status()
        run_detail = run_res.json()

        print(f"  Workflow Run Status: {run_detail['status']}")
        for step in run_detail.get("steps", []):
            s_name = step["step_name"]
            in_p = step.get("input_payload", {})
            out_p = step.get("output_payload", {})
            is_ref = isinstance(out_p, dict) and out_p.get("$apexflow_ref") is True
            print(f"  • Step '{s_name}': status={step['status']}, offloaded={is_ref}")
            print(f"    Input Payload : {in_p}")
            if is_ref:
                print(f"    📦 Output $apexflow_ref -> key: {out_p.get('key')}, size: {out_p.get('size_bytes')} bytes")
            else:
                summary = {k: v for k, v in out_p.items() if k != "sample"} if isinstance(out_p, dict) else out_p
                print(f"    Output Payload: {summary}")

    print("\n=========================================================")
    print("🎉 Large Payload Offloading Demo Completed Successfully!")
    print("=========================================================")


if __name__ == "__main__":
    asyncio.run(main())
