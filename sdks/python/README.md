# ApexFlow Python SDK (`apex-flow-sdk`)

> **Lightweight, Durable Workflow Orchestration Client for Python Applications.**

---

## 📦 Installation

```bash
pip install apex-flow-sdk
```

---

## ✨ Key Capabilities

- 🔄 **Durable Checkpointing**: Steps are memoized on completion; workflow execution resumes at the exact failed step without re-executing completed steps.
- 🔐 **Zero-Knowledge Payload Encryption (E2EE)**: Optional end-to-end authenticated AES-256-GCM client encryption (`encryption_key="secret"` or `APEXFLOW_ENCRYPTION_KEY`). PostgreSQL, Cloudflare R2, and control plane store only ciphertext. The Web dashboard decrypts payloads client-side in the browser via the Web Crypto API.
- ⚡ **Transparent Large Payload Offloading (`StorageResolver`)**: Payloads $> 250\text{ KB}$ are automatically offloaded to object storage (S3/MinIO) or local storage fallback via `StorageResolver`. The SDK transparently dereferences `$apexflow_ref` pointers back into native dictionaries or bytes.
- 🛡️ **Resilient Retries & Error Classification**: Configurable exponential backoff retries with immediate abort support for `NonRetryableError`.
- 🌲 **Parent-Child Lineage**: Launch child workflows via `ctx.child_workflow(...)` while maintaining full parent-child execution tracking.

---

## 🚀 Quickstart Example

```python
import asyncio
from apex_flow_sdk import ApexFlowClient, WorkflowContext

client = ApexFlowClient(
    base_url="http://localhost:8000",
    project_key="af_live_your_project_key",
    encryption_key="my-secret-passphrase",  # Optional: Zero-Knowledge E2EE
    worker_name="python-worker-01",
)

@client.workflow(name="process-lead-ai")
async def process_lead_workflow(ctx: WorkflowContext, user_input: str):
    # Step 1: Extract lead info
    extracted_data = await ctx.step(
        "extract-lead-info",
        lambda: {"name": "Alice", "company": "Acme Corp"},
        retries=3,
    )

    # Step 2: Create CRM record
    crm_record = await ctx.step(
        "create-crm-record",
        lambda: {"crm_id": "CRM-1002"},
    )

    return {"status": "completed", "crm_record": crm_record}
```

---

## 🏃 CLI Examples Runner (`examples/`)

Run interactive example walkthroughs using the built-in runner:

```bash
cd examples
./run.sh ecom        # Order fulfillment workflow demo
./run.sh ecom --fail # Failure simulation & retry demonstration
./run.sh sub         # Parent & child sub-workflow lineage demo
./run.sh large       # Large payload offloading demo (>250KB threshold)
./run.sh enc         # Zero-Knowledge client-side encryption demo (AES-256-GCM)
```

---

## 🧪 Running Automated E2E Tests

```bash
pytest tests/e2e/ -v
```
