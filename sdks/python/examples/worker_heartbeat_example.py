import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to sys.path so we can import apex_flow_sdk locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apex_flow_sdk import ApexFlowClient


async def main():
    base_url = os.getenv("APEXFLOW_BASE_URL", "http://127.0.0.1:8000")
    project_key = os.getenv("APEXFLOW_PROJECT_KEY")
    worker_name = os.getenv("APEXFLOW_WORKER_NAME", "worker-alpha-runner")

    print("=" * 60)
    print("💓 ApexFlow Worker Heartbeat Monitoring Demo")
    print("=" * 60)
    print(f"• Control Plane URL: {base_url}")
    print(f"• Worker Name      : {worker_name}")
    print(f"• Project Key      : {'[CONFIGURED]' if project_key else '[MISSING - will use dev mode]'}")
    print("\n👉 Open your browser at:")
    print("   http://localhost:3000/dashboard/workers")
    print("   to watch this worker's live ONLINE status and heartbeat updates.\n")

    client = ApexFlowClient(
        base_url=base_url,
        project_key=project_key,
        worker_name=worker_name,
    )

    duration_seconds = 20
    interval_seconds = 3
    total_beats = (duration_seconds // interval_seconds) + 1

    try:
        print(f"🚀 Starting heartbeat loop (sending every {interval_seconds}s for {duration_seconds}s)...")
        print("   (Press Ctrl+C to stop earlier)\n")

        for i in range(1, total_beats + 1):
            now_str = datetime.now().strftime("%H:%M:%S")
            await client.send_heartbeat()
            print(f"[{now_str}] 💓 Heartbeat #{i}/{total_beats} sent successfully (Status: ONLINE)")

            if i < total_beats:
                await asyncio.sleep(interval_seconds)

        print("\n✅ Heartbeat cycle completed successfully.")
        print("ℹ️  Note: In the dashboard, the worker will remain marked ONLINE for 60 seconds,")
        print("   then automatically transition to OFFLINE if no further heartbeats are received.")

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n🛑 Worker heartbeat loop interrupted by user.")
    except Exception as e:
        print(f"\n⚠️  Heartbeat error: {e}")
    finally:
        await client.close()
        print("🔒 Client session closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
