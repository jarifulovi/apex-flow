# ApexFlow Backend Control Plane (`apex-flow-backend`)

> **Asynchronous REST API State Coordinator, High-Throughput Queue Engine, and Execution Telemetry Provider.**

---

## 📌 Context & Overview

The **ApexFlow Backend Control Plane** is a lightweight, zero-knowledge state coordinator built with FastAPI and PostgreSQL. It manages workflow execution state, coordinates step-level queue sequencing, tracks worker heartbeats, and serves execution telemetry to the dashboard. 

The backend **never executes user business logic**, nor does it store sensitive API credentials or model keys. All workflow execution occurs locally on developer workers.

---

## 🛠️ Technology Stack & Dependency Specifications

| Component | Technology | Version Constraint | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | `>= 3.12` | High-performance asynchronous runtime. |
| **Framework** | FastAPI | `>= 0.110.0` | Asynchronous REST API & OpenAPI schema generator. |
| **ORM** | SQLAlchemy (Async) | `>= 2.0.0` | Non-blocking database models & query builder (`sqlalchemy[asyncio]`). |
| **Driver** | AsyncPG | `>= 0.30.0` | High-throughput PostgreSQL database driver. |
| **Config** | Pydantic Settings | `>= 2.0.0` | Type-safe environment configuration loader. |
| **Validation** | Pydantic | `>= 2.7.0` | Request serialization & payload schema validation. |
| **Security** | PyJWT | `>= 2.8.0` | Dashboard Supabase Bearer JWT decoding & validation. |
| **Testing** | Pytest & Pytest-Asyncio | `>= 8.0.0` | Automated integration and E2E test suite. |

---

## 🏗️ Architecture & Component Layers

```text
  [ Dashboard UI (Next.js) ]          [ SDK Worker Instances ]
             │                                   │
             ▼ (Bearer JWT)                      ▼ (X-ApexFlow-Project-Key)
    ┌──────────────────────────────────────────────────┐
    │           FastAPI API Router Layer               │
    │     (workflows.py, steps.py, keys.py, health.py)  │
    └────────────────────────┬─────────────────────────┘
                             │
                             ▼
    ┌──────────────────────────────────────────────────┐
    │               Service Engine Layer               │
    │ (WorkflowService, StepService, QueueService, etc)│
    └────────────────────────┬─────────────────────────┘
                             │
                             ▼
    ┌──────────────────────────────────────────────────┐
    │       Async SQLAlchemy ORM & Postgres DB         │
    │    (Projects, Workers, WorkflowRuns, Steps)      │
    └──────────────────────────────────────────────────┘
```

---

## ⚡ Key Backend Systems & Architecture Features

### 1. High-Throughput Scoped Queue Polling
- Uses PostgreSQL `SELECT FOR UPDATE OF WorkflowStep SKIP LOCKED`.
- Scoping row locks strictly to `workflow_steps` prevents table-level lock contention, allowing multiple workers to poll and execute steps for the same workflow run in parallel.
- Automatically recovers stale step leases (`recover_stale_locks`) if a worker process crashes or loses network connectivity mid-execution.

### 2. Fast $O(1)$ Step Status Reporting & Explicit SDK Completion
- Step execution reporting (`POST /api/v1/steps/report`) performs fast $O(1)$ status writes without expensive database subqueries or status guessing.
- Workflow run completion is triggered explicitly by the SDK (`POST /api/v1/workflows/{id}/complete`) when top-level workflow code finishes, avoiding premature status flips.

### 3. Idempotency & Deduplication Engine
- Supports optional `deduplication_id` on workflow creation (`POST /api/v1/workflows`).
- Enforces database-level idempotency via a filtered unique index (`idx_workflow_runs_dedup`), returning active workflow runs immediately if a duplicate trigger request is received.

### 4. Interactive Workflow Control Actions
- **Cancel Workflow** (`POST /api/v1/workflows/{id}/cancel`): Immediately cancels an active workflow run and marks all pending/queued steps as `cancelled`.
- **Restart Workflow** (`POST /api/v1/workflows/{id}/restart`): Resets failed or cancelled steps back to `queued` for worker pickup and re-activates the workflow run.

### 5. Worker Registry & Heartbeat Tracking
- Automatically registers workers and tracks active heartbeats (`name`, `worker_id`, `status`, `last_seen_at`) on every queue poll or step status report.

### 6. Dual Storage Retention & Pruning Strategy (`pg-cron`)
To prevent database storage bloating on Supabase free-tier PostgreSQL databases:
- **Soft Payload Pruning** (`prune_old_payloads`): Daily at 02:00 AM UTC, clears JSON payloads (`{}`) for completed runs older than 7 days, reducing disk usage by 90%+ while preserving run telemetry metrics for 30 days.
- **Hard Batched Delete** (`prune_old_workflow_runs_batched`): Daily at 03:00 AM UTC, deletes terminal runs older than 30 days in non-blocking batches of 2,000 rows.

---

## 🔒 Authentication & Multi-Tenant Security Model

The backend control plane enforces a **Two-Layer Authentication Model** (`app/api/deps.py`):

1. **SDK / Worker Authentication** (`X-ApexFlow-Project-Key`):
   - Authenticates worker requests via SHA-256 hashed Project API keys (`af_live_...`).
   - Automatically scopes queue polling, step creation, and workflow triggering to the key's project tenant.

2. **Dashboard UI Authentication** (`Bearer JWT`):
   - Authenticates dashboard requests via Supabase JWT Bearer tokens (`sub` claim).
   - Scopes project key management, tenant workflow telemetry, and manual control actions to the authenticated user.

---

## 🌐 Control Plane REST API Endpoint Summary

| Endpoint | Method | Auth Dependency | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | None | Liveness probe for cloud health checks (0 DB queries). |
| `/api/v1/health/db` | `GET` | None | Readiness probe checking live PostgreSQL database ping. |
| `/api/v1/keys` | `POST` | Supabase JWT | Create a new project API key (`raw_key` returned once). |
| `/api/v1/keys` | `GET` | Supabase JWT | List user's active & revoked project API keys. |
| `/api/v1/keys/{key_id}` | `DELETE` | Supabase JWT | Revoke a project API key by ID. |
| `/api/v1/workflows` | `POST` | Project API Key | Create or deduplicate a workflow run execution state. |
| `/api/v1/workflows` | `GET` | Bearer / Key | List workflow runs (paginated & filtered). |
| `/api/v1/workflows/{id}` | `GET` | Bearer / Key | Fetch workflow run detail and ordered step execution timeline. |
| `/api/v1/workflows/{id}/complete` | `POST` | Project API Key | Mark workflow run completed upon SDK function completion. |
| `/api/v1/workflows/{id}/cancel` | `POST` | Bearer / Key | Cancel active workflow run and mark queued steps cancelled. |
| `/api/v1/workflows/{id}/restart` | `POST` | Bearer / Key | Reset failed/cancelled steps to queued and restart run. |
| `/api/v1/steps` | `POST` | Project API Key | Queue a new step under a workflow run. |
| `/api/v1/steps/poll` | `POST` | Project API Key | Poll next queued step using `FOR UPDATE SKIP LOCKED`. |
| `/api/v1/steps/report` | `POST` | Project API Key | Report worker step execution result (`success` / `failed`). |
