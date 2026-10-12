# ApexFlow Python SDK Examples & Walkthroughs

This directory contains real-world usage examples demonstrating ApexFlow's durable code-first workflow orchestration, worker step queues, and telemetry monitoring.

---

## 🛠️ Prerequisites

1. **Backend Running**: Ensure FastAPI backend is running (`./dev.sh` or `uvicorn app.main:app --port 8000`).
2. **Dashboard Running**: Next.js Dashboard (`npm run dev` in `apex-flow-dashboard`).
3. **API Project Key**:
   - Go to `http://localhost:3000/dashboard/project-keys`.
   - Click **New Key** to generate an API key (e.g. `apx_live_...`).
   - Copy `.env.example` to `.env` in this folder or set environment variable:
     ```bash
     export APEXFLOW_PROJECT_KEY="apx_live_your_key_here"
     ```

---

## 📦 Walkthrough 1: E-Commerce Order Processing Pipeline

File: [`ecommerce_order_processing.py`](file:///home/ovi/Desktop/Project/Web/apex-flow/sdks/python/examples/ecommerce_order_processing.py)

Demonstrates a multi-step order fulfillment pipeline (`validate-payment` ➔ `reserve-inventory` ➔ `generate-shipping-label` ➔ `send-dispatch-email`).

### Run Options:
```bash
./run.sh ecom               # Standard execution
./run.sh ecom --fail        # Simulated step failure & retries
./run.sh subworkflow        # Parent & Child Sub-Workflow Lineage Demo
```

### What happens:
1. Registers a new workflow run execution on ApexFlow backend.
2. Executes each step with zero-knowledge durable checkpointing.
3. Spawns child sub-workflows linked by `parent_workflow_id` when running `--subworkflow`.
4. Live telemetry updates automatically in your Dashboard under **Workflows** (`/dashboard/workflows`) and **Steps** (`/dashboard/steps`).

---

## 🌿 Parent-Child Sub-Workflow State Behavior Matrix

| Scenario | Fire-and-Forget Mode (Async) | Awaited Sub-Workflow Mode (Sync) |
| :--- | :--- | :--- |
| **Child Fails** | Child $\rightarrow$ `FAILED`. Parent stays `COMPLETED`. | Child $\rightarrow$ `FAILED`. Parent step catches error $\rightarrow$ Parent `FAILED`. |
| **Child Cancelled** | Child $\rightarrow$ `CANCELLED`. Parent unaffected. | Child $\rightarrow$ `CANCELLED`. Parent step fails $\rightarrow$ Parent `FAILED`. |
| **Child Restarted** | Child reset to `PENDING`. Parent unaffected. | Child reset to `PENDING`. Parent re-awaits child result. |
| **Parent Fails** | Parent $\rightarrow$ `FAILED`. Active child workflows continue running. | Parent $\rightarrow$ `FAILED`. Active child workflows continue running. |
| **Parent Cancelled** | Parent $\rightarrow$ `CANCELLED`. Cascades `CANCELLED` to active child workflows. | Parent $\rightarrow$ `CANCELLED`. Cascades `CANCELLED` to active child workflows. |
| **Parent Restarted** | Parent reset to `RUNNING`. Cascades `PENDING` reset to failed/cancelled child workflows. | Parent reset to `RUNNING`. Cascades `PENDING` reset to failed/cancelled child workflows. |

---

## ⚡ Walkthrough 2: AI Lead Processing & Worker Queue

File: [`worker_example.py`](file:///home/ovi/Desktop/Project/Web/apex-flow/sdks/python/examples/worker_example.py)

Demonstrates AI lead ingestion with worker step queues.

### Run:
```bash
./run.sh lead
```

---

## 📦 Walkthrough 3: Large Payload Offloading Demo

File: [`large_payload_example.py`](file:///home/ovi/Desktop/Project/Web/apex-flow/sdks/python/examples/large_payload_example.py)

Demonstrates automatic offloading of large step payloads ($> 250\text{ KB}$) to Cloudflare R2 / S3 or local disk storage via `StorageResolver`.

### Run:
```bash
./run.sh large
```

---

## 🔐 Walkthrough 4: Zero-Knowledge Payload Encryption (E2EE)

File: [`encrypted_payload_example.py`](file:///home/ovi/Desktop/Project/Web/apex-flow/sdks/python/examples/encrypted_payload_example.py)

Demonstrates end-to-end client-side authenticated AES-256-GCM encryption. Sensitive payroll, PII, and financial inputs/outputs are encrypted prior to network transmission.

- **PostgreSQL / Storage Engine**: Stores only ciphertext envelopes (`$apexflow_encrypted: true`, `iv`, `ciphertext`, `key_hint`).
- **Dashboard Inspection**: Decrypted client-side in the browser via Web Crypto API with instant lock/unlock UI.
- **Crash Recovery**: Recovering workers with the matching encryption key automatically decrypt checkpoints and continue execution seamlessly.

### Run:
```bash
./run.sh enc
```
