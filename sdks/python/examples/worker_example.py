import asyncio
import os
import uuid
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to sys.path so we can import apex_flow_sdk locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apex_flow_sdk import ApexFlowClient, WorkflowContext

# Initialize the client. 
# It will automatically pick up APEXFLOW_PROJECT_KEY and APEXFLOW_BASE_URL from the environment,
# or you can pass them explicitly:
client = ApexFlowClient(
    base_url=os.getenv("APEXFLOW_BASE_URL", "http://127.0.0.1:8000"),
    project_key=os.getenv("APEXFLOW_PROJECT_KEY")
)

@client.workflow(name="hello_world_workflow")
async def hello_world(ctx: WorkflowContext, name: str):
    print(f"Executing hello_world workflow for: {name}")
    
    # You can imagine step logic going here
    # e.g., result = await ctx.step(some_task, name)
    
    return f"Hello, {name}!"

async def main():
    print("--- ApexFlow Python SDK Example ---")
    
    # Example: Triggering a workflow programmatically
    try:
        user_id = uuid.uuid4()
        print(f"Triggering workflow for user: {user_id}")
        workflow_id = await client.trigger_workflow("hello_world_workflow", user_id)
        print(f"✅ Workflow triggered successfully. ID: {workflow_id}")
    except Exception as e:
        print(f"Failed to trigger workflow. Did you set APEXFLOW_PROJECT_KEY? Error: {e}")

    print("\nStarting worker loop... (Press Ctrl+C to stop)")
    # Start the worker to poll for tasks from the backend
    try:
        await client.start_worker(poll_interval=2.0)
    except KeyboardInterrupt:
        print("Worker stopped.")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
