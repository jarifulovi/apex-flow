import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to sys.path so we can import apex_flow_sdk locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apex_flow_sdk import ApexFlowClient, WorkflowContext

# Initialize client
client = ApexFlowClient(
    base_url=os.getenv("APEXFLOW_BASE_URL", "http://127.0.0.1:8000"),
    project_key=os.getenv("APEXFLOW_PROJECT_KEY"),
    worker_name="lead-processing-worker",
)


@client.workflow(name="process-lead-ai")
async def process_lead_workflow(ctx: WorkflowContext, user_input: dict):
    print(f"\n⚡ Executing process-lead-ai workflow run: {ctx.workflow_run_id}")

    # Step 1: Extract lead information
    extracted_data = await ctx.step(
        "extract-lead-info",
        lambda: {"lead_name": "Alice Developer", "company": "ApexTech", "email": "alice@example.com"},
        retries=3,
    )
    print(f"✅ Step 1 complete: Extracted lead '{extracted_data['lead_name']}'")

    # Step 2: Create CRM Record
    crm_id = await ctx.step(
        "create-crm-record",
        lambda: {"crm_id": f"CRM-{extracted_data['company'].upper()}-99"},
        retries=3,
    )
    print(f"✅ Step 2 complete: Created CRM record '{crm_id['crm_id']}'")

    # Step 3: Send Confirmation Email
    confirmation = await ctx.step(
        "send-welcome-email",
        lambda: {"status": "sent", "recipient": extracted_data["email"]},
        retries=2,
    )
    print(f"✅ Step 3 complete: Confirmation email sent to {confirmation['recipient']}")

    return {"status": "completed", "crm_id": crm_id["crm_id"]}


async def main():
    print("--- ApexFlow Python SDK Workflow & Worker Example ---")

    try:
        print("Triggering workflow 'process-lead-ai'...")
        workflow_run_id = await client.trigger_workflow(
            name="process-lead-ai",
            metadata={"source": "example_script", "env": "development"},
        )
        print(f"✅ Workflow run triggered successfully. Run ID: {workflow_run_id}")

        # Execute workflow instance locally
        ctx = WorkflowContext(workflow_run_id=workflow_run_id, client=client)
        result = await process_lead_workflow(ctx, {"lead_raw_input": "Alice from ApexTech"})
        print(f"\n🎉 Workflow Execution Finished! Final Result: {result}")

    except Exception as e:
        print(f"⚠️ Error running workflow: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
