# ApexFlow Workflow Specification (`docs/WORKFLOW_SPEC.md`)

> **Workflow Lifecycles, Step Execution Mechanics, Sub-Workflow Lineage, and Queue Specifications.**

---

## 📌 Overview

ApexFlow orchestrates multi-step business logic by decomposing applications into **discrete domain workflows** composed of individual, durable **steps**.

Workflows operate on a code-first, event-driven execution model where control plane state transitions occur asynchronously while step functions execute on distributed worker processes.

---

## 🔄 Modular Domain Workflow Models

Rather than running monolithic scripts, applications in ApexFlow are structured as modular domain workflows:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Workflow 1: Lead Enrichment & Sales Pipeline                                │
│ [ Extract Lead ] ──> [ Enrich CRM Data ] ──> [ Score ] ──> [ Trigger Email ] │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Workflow 2: E-Commerce Order Fulfillment & Logistics                         │
│ [ Validate Payment ] ──> [ Lock Inventory ] ──> [ Label ] ──> [ Dispatch ]  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Workflow 3: Multi-Stage AI Data Ingestion                                   │
│ [ Fetch Doc ] ──> [ Chunk & Embed Vectors ] ──> [ Summarize ] ──> [ Index ] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Master Workflow Run Lifecycle

A **Workflow Run** represents a single execution instance of a named workflow.

```text
                      ┌──(all steps success + complete signal)──> [ COMPLETED ]
                      │
[ PENDING ] ──> [ RUNNING ] ───┬──(unhandled error or abort)────> [ FAILED ]
                      │        │
                      │        └──(manual cancel action)────────> [ CANCELLED ]
                      │
                      └──(manual restart action)────────────────> [ RUNNING ]
```

### Lifecycle States:
- **`PENDING`**: Workflow run has been registered on the control plane; execution has not yet commenced.
- **`RUNNING`**: First step has been acquired by a worker or step execution is actively in progress.
- **`COMPLETED`**: All steps finished with `success` and top-level workflow code sent an explicit completion signal.
- **`FAILED`**: A step encountered a non-retryable error or exhausted retry limits.
- **`CANCELLED`**: Execution was manually terminated via the control plane API or dashboard.

### Key Operational Rules:
1. **Idempotency & Deduplication**: If triggered with a `deduplication_id`, the control plane checks for an existing active run (`PENDING` or `RUNNING`) and returns the existing run ID, preventing duplicate workflow executions.
2. **Interactive Restart**: Failed or cancelled runs can be restarted, resetting terminal step statuses back to `QUEUED` while preserving previously completed step checkpoints.

---

## ⚙️ Individual Step Lifecycle Mechanics

A **Workflow Step** represents an atomic unit of execution within a workflow run (e.g. an API call, database mutation, or model inference).

```text
[ QUEUED ] ──(worker poll SKIP LOCKED)──> [ RUNNING ] ──┬──(report success)──> [ SUCCESS ]
                                                        │
                                                        └──(retries exhausted)─> [ FAILED ]
```

### Lifecycle States:
- **`QUEUED`**: Registered in the control plane database queue awaiting worker pickup.
- **`RUNNING`**: Acquired by a worker process via PostgreSQL row locking (`FOR UPDATE SKIP LOCKED`).
- **`SUCCESS`**: Executed successfully on worker; output payload memoized.
- **`FAILED`**: Encountered a non-retryable failure or exhausted max attempt limits.
- **`CANCELLED`**: Marked cancelled due to parent workflow cancellation.

### Step Execution Guarantees:
- **Sequence Tracking (`step_order`)**: Each step is assigned a 1-based integer sequence (`step_order = 1, 2, 3...`), guaranteeing deterministic chronological ordering in database timeline queries.
- **Concurrency & Non-Blocking Polling**: Workers poll queued steps using PostgreSQL `FOR UPDATE OF WorkflowStep SKIP LOCKED`. Workers lock only the specific step row, allowing multiple workers to poll steps for the same workflow in parallel without lock contention.
- **Lease Locking & Stale Recovery**: Acquired steps receive a temporary lease lock (`locked_until`). If a worker crashes, the control plane automatically re-queues expired steps (`recover_stale_locks`).

---

## 🌲 Parent-Child Sub-Workflow Lineage

ApexFlow supports launching **sub-workflows** from within parent workflow steps:

```text
[ Master Order Workflow (Run #101) ]
       │
       ├── Step 1: Validate Payment
       │
       ├── Step 2: Launch Fulfillment Sub-Workflow (Run #102, parent_workflow_id=#101)
       │       │
       │       ├── Child Step 2a: Lock Warehouse Inventory
       │       └── Child Step 2b: Print Shipping Label
       │
       └── Step 3: Send Confirmation Email
```

### Sub-Workflow Rules:
- **Hierarchical Tracking**: Child workflows store `parent_workflow_id`, establishing strict parent-child lineage.
- **Dashboard Tree Telemetry**: Allows visual dashboard inspectors to render nested execution trees and trace parent-child status propagation.
- **Modular Isolation**: Sub-workflows maintain independent retry budgets, step order sequences, and status lifecycles.

---

## 🌐 Control Plane Protocol Map

| Action | Endpoint | Purpose |
| :--- | :--- | :--- |
| **Trigger Workflow** | `POST /api/v1/workflows` | Register or deduplicate a master workflow run. |
| **Queue Step** | `POST /api/v1/steps` | Register an individual step in `QUEUED` state. |
| **Poll Step** | `POST /api/v1/steps/poll` | Acquire next queued step via row-level locking. |
| **Report Status** | `POST /api/v1/steps/report` | Update step status (`SUCCESS` / `FAILED`). |
| **Complete Workflow** | `POST /api/v1/workflows/{id}/complete` | Transition run to `COMPLETED`. |
| **Cancel Run** | `POST /api/v1/workflows/{id}/cancel` | Cancel active run and pending steps. |
| **Restart Run** | `POST /api/v1/workflows/{id}/restart` | Reset failed steps to `QUEUED` and re-activate run. |
