"""
ApexFlow E-Commerce Order Processing Workflow Example
======================================================
Demonstrates a multi-step durable order processing pipeline using the Python SDK.

Steps:
  1. validate-payment         : Reserve funds and verify transaction token (with retry resilience)
  2. reserve-inventory        : Lock warehouse stock for ordered items
  3. generate-shipping-label  : Create carrier tracking label & dispatch manifest
  4. send-dispatch-email      : Send order confirmation to customer

Run Modes:
  - Normal Walkthrough: ./run.sh ecom
  - Failure Simulation: ./run.sh ecom --fail (Demonstrates retries, step failure, and error inspection)
"""

import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add SDK root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apex_flow_sdk import ApexFlowClient, WorkflowContext, validate_response, NonRetryableError

# Check for failure simulation flag
SIMULATE_FAILURE = "--fail" in sys.argv or "--simulate-failure" in sys.argv

# Initialize SDK Client
BASE_URL = os.getenv("APEXFLOW_BASE_URL", "http://127.0.0.1:8000")
PROJECT_KEY = os.getenv("APEXFLOW_PROJECT_KEY")

client = ApexFlowClient(
    base_url=BASE_URL,
    project_key=PROJECT_KEY,
    worker_name="fulfillment-center-worker-01",
)


# Define Workflow
@client.workflow(name="ecommerce-order-pipeline")
async def process_order_workflow(ctx: WorkflowContext, order_details: dict):
    print(f"\n📦 [ApexFlow] Processing Order Workflow Run: {ctx.workflow_run_id}")
    order_id = order_details.get("order_id", f"ORD-{uuid.uuid4().hex[:6].upper()}")
    total_amount = order_details.get("amount", 289.50)

    payment_attempt = 0

    # Step 1: Validate Payment (demonstrating retries and validate_response)
    async def validate_payment_func():
        nonlocal payment_attempt
        payment_attempt += 1
        print(f"  💳 [Step 1 (Attempt #{payment_attempt})] Validating payment of ${total_amount:.2f} for Order {order_id}...")
        await asyncio.sleep(0.4)

        if SIMULATE_FAILURE and payment_attempt == 1:
            print("  ⚠️ [Step 1 Simulated Failure] Gateway timeout! Triggering SDK retry...")
            # Returning a silent error structure that validate_response converts to retryable ValueError
            raw_response = {"success": False, "error": "Gateway Timeout (504)"}
        else:
            raw_response = {
                "success": True,
                "payment_status": "SUCCESS",
                "transaction_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
                "amount_charged": total_amount,
            }

        # Validate response payload against silent API errors
        return validate_response(raw_response)

    payment_res = await ctx.step("validate-payment", validate_payment_func, retries=3, backoff_factor=0.5)
    print(f"  ✅ [Step 1 Passed] Payment Approved! Txn ID: {payment_res['transaction_id']}")

    # Step 2: Reserve Inventory
    async def reserve_inventory_func():
        print(f"  🏭 [Step 2] Locking warehouse inventory for {len(order_details.get('items', []))} items...")
        await asyncio.sleep(0.4)

        if SIMULATE_FAILURE and order_details.get("force_item_out_of_stock"):
            print("  ❌ [Step 2 Simulated Fatal Error] SKU OUT_OF_STOCK! Raising NonRetryableError...")
            raise NonRetryableError("SKU #KB-809 OUT_OF_STOCK: Insufficient units at WH-EAST-04")

        return {
            "warehouse_id": "WH-EAST-04",
            "items_allocated": order_details.get("items", ["Mechanical Keyboard", "Monitor Arm"]),
            "status": "RESERVED",
        }

    inventory_res = await ctx.step("reserve-inventory", reserve_inventory_func, retries=3)
    print(f"  ✅ [Step 2 Passed] Inventory Locked at {inventory_res['warehouse_id']}")

    # Step 3: Generate Shipping Label
    async def generate_shipping_label_func():
        print(f"  🚚 [Step 3] Generating carrier shipping label for {order_details.get('customer_email')}...")
        await asyncio.sleep(0.4)
        return {
            "carrier": "FedEx Express",
            "tracking_number": f"TRK-{uuid.uuid4().hex[:10].upper()}",
            "label_url": f"https://labels.apexflow.io/{order_id}.pdf",
        }

    shipping_res = await ctx.step("generate-shipping-label", generate_shipping_label_func, retries=3)
    print(f"  ✅ [Step 3 Passed] Label Ready! Carrier: {shipping_res['carrier']} | Tracking: {shipping_res['tracking_number']}")

    # Step 4: Dispatch Notification
    async def send_dispatch_email_func():
        email = order_details.get("customer_email", "customer@example.com")
        print(f"  📧 [Step 4] Sending dispatch confirmation email to {email}...")
        await asyncio.sleep(0.3)
        return {
            "notification_sent": True,
            "recipient": email,
            "tracking_number": shipping_res["tracking_number"],
        }

    notify_res = await ctx.step("send-dispatch-email", send_dispatch_email_func, retries=2)
    print(f"  ✅ [Step 4 Passed] Confirmation Email Delivered to {notify_res['recipient']}")

    # Return Final Order Summary
    return {
        "status": "ORDER_FULFILLED",
        "order_id": order_id,
        "transaction_id": payment_res["transaction_id"],
        "tracking_number": shipping_res["tracking_number"],
        "warehouse": inventory_res["warehouse_id"],
    }


async def main():
    print("=" * 65)
    print("🚀 ApexFlow E-Commerce Order Processing Workflow Walkthrough")
    if SIMULATE_FAILURE:
        print("⚡ SIMULATED FAILURE MODE ACTIVE (--fail)")
    print("=" * 65)

    if not PROJECT_KEY:
        print("⚠️ WARNING: APEXFLOW_PROJECT_KEY environment variable is not set.")
        print("   Create a Project Key in http://localhost:3000/dashboard -> Project Keys")
        print("   and add it to .env or export APEXFLOW_PROJECT_KEY='apx_live_...'")
        print("-" * 65)

    order_payload = {
        "order_id": f"ORD-{uuid.uuid4().hex[:6].upper()}",
        "customer_email": "jane.doe@example.com",
        "amount": 289.50,
        "items": ["Ergonomic Mechanical Keyboard", "UltraWide Monitor Arm"],
        "force_item_out_of_stock": SIMULATE_FAILURE,
    }

    try:
        # 1. Trigger Workflow Run on ApexFlow Control Plane
        print(f"1. Registering new workflow run for Order: {order_payload['order_id']}...")
        workflow_run_id = await client.trigger_workflow(
            name="ecommerce-order-pipeline",
            metadata={
                "order_id": order_payload["order_id"],
                "customer": order_payload["customer_email"],
                "simulation": "failure" if SIMULATE_FAILURE else "normal",
            },
        )
        print(f"   Registered Control Plane Workflow Run ID: {workflow_run_id}\n")

        # 2. Execute Workflow Steps locally with durable checkpointing
        ctx = WorkflowContext(workflow_run_id=workflow_run_id, client=client)
        result = await process_order_workflow(ctx, order_payload)

        print("\n" + "=" * 65)
        print("🎉 WORKFLOW FULFILLMENT COMPLETED SUCCESSFULLY!")
        print(f"   Order ID       : {result['order_id']}")
        print(f"   Transaction ID : {result['transaction_id']}")
        print(f"   Tracking No    : {result['tracking_number']}")
        print(f"   Warehouse      : {result['warehouse']}")
        print("   Check live telemetry at: http://localhost:3000/dashboard/workflows")
        print("=" * 65)

    except Exception as e:
        print("\n" + "=" * 65)
        print(f"❌ WORKFLOW EXECUTION FAILED AS EXPECTED IN SIMULATION MODE!")
        print(f"   Error Details: {e}")
        print("   Inspect the error traceback & test 'Restart Run' at:")
        print("   http://localhost:3000/dashboard/workflows")
        print("=" * 65)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

