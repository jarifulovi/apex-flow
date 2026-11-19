import argparse
import asyncio
from datetime import datetime, timezone
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file in this directory
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add the parent SDK directory to sys.path so apex_flow_sdk can be imported locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apex_flow_sdk import ApexFlowClient, WorkflowContext


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ApexFlow Cron & Scheduled Workflow Worker Demo"
    )
    parser.add_argument(
        "--cron",
        default="*/2 * * * *",
        help="5-field cron expression (default: '*/2 * * * *', every 2 minutes)",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone name for cron evaluation (default: 'UTC')",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    base_url = os.getenv("APEXFLOW_BASE_URL", "http://127.0.0.1:8000")
    project_key = os.getenv("APEXFLOW_PROJECT_KEY")
    worker_name = os.getenv("APEXFLOW_WORKER_NAME", "cron-scheduler-worker")

    print("=" * 64)
    print("⏰ ApexFlow Cron & Scheduled Workflow Example")
    print("=" * 64)
    print(f"• Control Plane URL : {base_url}")
    print(f"• Worker Name       : {worker_name}")
    print(f"• Workflow Name     : scheduled-health-report")
    print(f"• Cron Expression   : {args.cron} ({args.timezone})")
    print(f"• Project Key       : {'[CONFIGURED]' if project_key else '[MISSING]'}")
    print("\n👉 Open your browser at:")
    print("   http://localhost:3000/dashboard/workflows?tab=schedules")
    print("   to inspect the auto-synced schedule, pause/resume it, or click 'Run Now'.\n")

    client = ApexFlowClient(
        base_url=base_url,
        project_key=project_key,
        worker_name=worker_name,
    )

    @client.workflow(
        name="scheduled-health-report",
        cron=args.cron,
        timezone=args.timezone,
    )
    async def scheduled_health_report(ctx: WorkflowContext, trigger_payload: dict):
        trigger_source = (
            trigger_payload.get("trigger_source", "schedule")
            if isinstance(trigger_payload, dict)
            else "schedule"
        )
        print(
            f"\n⚡ Running 'scheduled-health-report' (run={ctx.workflow_run_id}, source={trigger_source})"
        )

        metrics = await ctx.step(
            "collect-service-metrics",
            lambda: {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "api_p95_ms": 42.5,
                "error_rate_pct": 0.08,
                "active_connections": 14,
            },
            retries=2,
        )
        print(f"   ✅ Collected metrics: p95={metrics['api_p95_ms']}ms")

        summary = await ctx.step(
            "publish-health-summary",
            lambda: {
                "status": "healthy",
                "trigger_source": trigger_source,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "p95_ms": metrics["api_p95_ms"],
            },
            retries=2,
        )
        print(f"   ✅ Published summary: {summary['status']} ({summary['reported_at']})")
        return summary

    try:
        print("🚀 Starting worker (syncing cron schedule on startup, press Ctrl+C to stop)...")
        await client.start_worker()
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n🛑 Cron worker stopped by user.")
    finally:
        await client.close()
        print("🔒 Client session closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

