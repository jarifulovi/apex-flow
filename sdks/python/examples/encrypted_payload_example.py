import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add SDK root to path for local development
SDK_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SDK_ROOT))

import httpx
from apex_flow_sdk import ApexFlowClient, WorkflowContext


# Client automatically resolves APEXFLOW_BASE_URL, APEXFLOW_PROJECT_KEY,
# and APEXFLOW_ENCRYPTION_KEY from environment variables / .env
client = ApexFlowClient(
    worker_name="payroll-crypto-worker",
)
ENCRYPTION_KEY = client.encryption_key or "demo-secret-passphrase-2026"


@client.workflow("confidential_payroll_pipeline")
async def confidential_payroll_pipeline(ctx: WorkflowContext, input_data: dict):
    print("🔒 [Workflow] Starting Confidential Payroll Processing Pipeline...")

    # Step 1: Ingest sensitive employee compensation
    async def ingest_sensitive_employee_records():
        print("  ⚡ [Step 1] Processing sensitive PII and salary records...")
        return {
            "employee_id": "EMP-8081",
            "name": "Alex Mercer",
            "ssn": "987-65-4321",
            "salary_usd": 165000.0,
            "bonus_usd": 22500.0,
            "bank_account": "US-ACH-4411990022",
        }

    employee_data = await ctx.step(
        "ingest_employee_pii",
        ingest_sensitive_employee_records,
        input_payload={"department": "Security Architecture", "level": "Principal"},
    )
    print(f"  ✅ [Step 1 Completed] Ingested employee: {employee_data['name']} (SSN: {employee_data['ssn']})")

    # Step 2: Compute net compensation and disbursements
    async def calculate_disbursement(data: dict):
        print(f"  ⚡ [Step 2] Calculating net disbursement for {data['name']}...")
        gross = data["salary_usd"] + data["bonus_usd"]
        tax_withholding = gross * 0.28
        net = gross - tax_withholding
        return {
            "employee_id": data["employee_id"],
            "gross_total": gross,
            "tax_withheld": tax_withholding,
            "net_disbursement": net,
            "status": "APPROVED_FOR_DISBURSEMENT",
        }

    disbursement = await ctx.step(
        "calculate_disbursement",
        calculate_disbursement,
        input_payload=employee_data,
    )
    print(f"  ✅ [Step 2 Completed] Net disbursement calculated: ${disbursement['net_disbursement']:,.2f}")
    return disbursement


async def main():
    print("=========================================================")
    print("🔐 ApexFlow: Zero-Knowledge Payload Encryption Demo")
    print("=========================================================")
    print(f"🔑 Client Encryption Key: '{ENCRYPTION_KEY}'")

    # 1. Trigger workflow run
    print("\n1️⃣ Triggering 'confidential_payroll_pipeline' workflow run...")
    run_id = await client.trigger_workflow(
        name="confidential_payroll_pipeline",
        metadata={"classification": "RESTRICTED_PII", "e2ee": True},
    )
    print(f"  ✅ Triggered Workflow Run ID: {run_id}")

    # 2. Execute workflow pipeline locally with client-side encryption
    print("\n2️⃣ Executing workflow steps with client-side AES-256-GCM encryption...")
    ctx = WorkflowContext(workflow_run_id=run_id, client=client)
    result = await confidential_payroll_pipeline(ctx, {"batch": "2026-Q4"})

    # 3. Inspect control plane database state to prove zero-knowledge storage
    print("\n3️⃣ Inspecting Control Plane DB state (what PostgreSQL & Cloudflare R2 see)...")
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

            is_enc_in = isinstance(in_p, dict) and in_p.get("$apexflow_encrypted") is True
            is_enc_out = isinstance(out_p, dict) and out_p.get("$apexflow_encrypted") is True

            print(f"\n  • Step '{s_name}': status={step['status']}")
            print(f"    Input Payload (Stored in DB):")
            print(f"      Encrypted: {is_enc_in}")
            if is_enc_in:
                print(f"      Ciphertext Preview: {in_p.get('ciphertext')[:36]}... [Algorithm: {in_p.get('alg')}]")
            else:
                print(f"      Raw Data: {in_p}")

            print(f"    Output Payload (Stored in DB):")
            print(f"      Encrypted: {is_enc_out}")
            if is_enc_out:
                print(f"      Ciphertext Preview: {out_p.get('ciphertext')[:36]}... [Algorithm: {out_p.get('alg')}]")
                print(f"      Key Hint: {out_p.get('key_hint')} (SSN and salary are completely hidden from server!)")
            else:
                print(f"      Raw Data: {out_p}")

    print("\n=========================================================")
    print("🎉 Zero-Knowledge Encryption Demo Completed Successfully!")
    print("   Open your ApexFlow Dashboard to inspect the payload.")
    print(f"   Use decryption passphrase: '{ENCRYPTION_KEY}'")
    print("=========================================================")


if __name__ == "__main__":
    asyncio.run(main())
