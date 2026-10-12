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

    # Step 3: Archive massive confidential payroll audit vault (> 250 KB)
    # Automatically triggers BOTH Zero-Knowledge Encryption AND Cloud Provider offloading!
    async def archive_bulk_audit_vault():
        print("  ⚡ [Step 3] Generating 1,200 confidential compensation audit records (~360 KB)...")
        records = [
            {
                "audit_id": f"AUD-2026-{i:05d}",
                "employee_id": f"EMP-{(1000 + i % 300)}",
                "tax_id": f"987-{i % 100:02d}-{(i * 73) % 10000:04d}",
                "disbursement_usd": 120000.0 + (i * 35.25),
                "routing_number": f"FED-ACH-{(10000000 + i * 19):09d}",
                "classification": "RESTRICTED_PII_OFFLOADED_VAULT",
                "audit_note": "Zero-knowledge authenticated AES-256-GCM ciphertext offloaded to Cloudflare R2 / S3.",
            }
            for i in range(1200)
        ]
        return {
            "vault_batch": "PAYROLL-VAULT-2026-FINAL",
            "record_count": len(records),
            "records": records,
        }

    archived_vault = await ctx.step(
        "archive_bulk_audit_vault",
        archive_bulk_audit_vault,
        input_payload={"vault_tier": "cold_storage_r2", "target_records": 1200},
    )
    print(f"  ✅ [Step 3 Completed] Archived {archived_vault['record_count']} confidential records locally.")
    return archived_vault


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

    # 3. Inspect control plane database state & cloud storage object to prove zero-knowledge storage
    print("\n3️⃣ Inspecting Control Plane DB & Cloud Storage state...")
    headers = {"X-ApexFlow-Project-Key": client.project_key} if client.project_key else {}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as http:
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
            is_ref_out = isinstance(out_p, dict) and out_p.get("$apexflow_ref") is True

            print(f"\n  • Step '{s_name}': status={step['status']}")
            print(f"    Input Payload (PostgreSQL DB):")
            if is_enc_in:
                print(f"      Ciphertext Preview: {in_p.get('ciphertext')[:36]}... [Algorithm: {in_p.get('alg')}]")
            else:
                print(f"      Raw Data: {in_p}")

            print(f"    Output Payload (PostgreSQL DB):")
            if is_enc_out:
                print(f"      Ciphertext Preview: {out_p.get('ciphertext')[:36]}... [Algorithm: {out_p.get('alg')}]")
                print(f"      Key Hint Fingerprint: {out_p.get('key_hint')}")
            elif is_ref_out:
                print(f"      📦 OFFLOADED TO CLOUD STORAGE (Threshold > 250KB triggered!)")
                print(f"      Descriptor Key: {out_p.get('key')}")
                print(f"      Provider: {out_p.get('provider')} | Size: {out_p.get('size_bytes'):,} bytes (~{out_p.get('size_bytes')/1024:.1f} KB)")
                print(f"      Descriptor Encrypted Flag: {out_p.get('encrypted')} | Key Hint: {out_p.get('key_hint')}")

                # 4. Fetch the raw cloud object directly from storage to inspect its actual bytes in the bucket
                storage_url = f"{client.base_url}/api/v1/storage/download/{out_p['key']}"
                cloud_file_res = await http.get(storage_url)
                if cloud_file_res.status_code == 200:
                    cloud_json = cloud_file_res.json()
                    is_cloud_blob_enc = isinstance(cloud_json, dict) and cloud_json.get("$apexflow_encrypted") is True
                    print(f"\n    ☁️  RAW CLOUD BUCKET INSPECTION ({out_p.get('provider', 'S3').upper()} Object Content):")
                    print(f"      Object in Cloud Provider is Encrypted: {is_cloud_blob_enc}")
                    print(f"      Ciphertext Preview in Bucket: {cloud_json.get('ciphertext')[:40]}...")
                    print(f"      Plaintext 'records' visible to Cloud Provider: {'records' in cloud_json} (100% Zero-Knowledge!)")

                # 5. Test local worker decryption via StorageResolver
                from apex_flow_sdk.adapters.storage import StorageResolver
                from apex_flow_sdk.core.encryption import decrypt_if_encrypted
                resolved_blob = await StorageResolver.resolve_payload(client.http_client, client.base_url, out_p)
                decrypted_blob = decrypt_if_encrypted(resolved_blob, client.encryption_key)
                rec_count = len(decrypted_blob.get("records", [])) if isinstance(decrypted_blob, dict) else 0
                print(f"      Worker Decryption Test: Decrypted {rec_count:,} records in memory successfully!")
            else:
                print(f"      Raw Data: {out_p}")

    print("\n================================================================================")
    print("🎉 Zero-Knowledge File Storage & Encryption Demo Completed Successfully!")
    print("================================================================================")
    print(f"👉 How to manually verify in your Dashboard:")
    print(f"   1. Open: http://localhost:3000/dashboard/workflows/{run_id}")
    print(f"   2. View Step 3 ('archive_bulk_audit_vault') and click 'View Payload'.")
    print(f"   3. Click 'Download Payload' -> You will download the RAW cloud JSON file.")
    print(f"      Open it in any text editor -> Notice it is 100% ciphertext (zero plaintext).")
    print(f"   4. Enter your passphrase '{ENCRYPTION_KEY}' into the modal and click 'Decrypt'.")
    print(f"      The modal will decrypt the 1,200 records client-side in your browser!")
    print(f"   5. Click 'Decrypted JSON' to download the decrypted plain records.")
    print("================================================================================")


if __name__ == "__main__":
    asyncio.run(main())
