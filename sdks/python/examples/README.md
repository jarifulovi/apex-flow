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

### Run:
```bash
python sdks/python/examples/ecommerce_order_processing.py
```

### What happens:
1. Registers a new workflow run execution on ApexFlow backend.
2. Executes each step with zero-knowledge durable checkpointing.
3. Live telemetry updates automatically in your Dashboard under **Workflows** (`/dashboard/workflows`) and **Steps** (`/dashboard/steps`).

---

## ⚡ Walkthrough 2: AI Lead Processing & Worker Queue

File: [`worker_example.py`](file:///home/ovi/Desktop/Project/Web/apex-flow/sdks/python/examples/worker_example.py)

Demonstrates AI lead ingestion with worker step queues.

### Run:
```bash
python sdks/python/examples/worker_example.py
```
