# ApexFlow Backend Control Plane (`apex-flow-backend`)

> **Asynchronous REST API State Coordinator, High-Throughput Queue Engine, and Execution Telemetry Provider.**

---

## 📌 Context & Overview

The **ApexFlow Backend Control Plane** is a lightweight, zero-knowledge state coordinator built with FastAPI and PostgreSQL. It manages workflow execution state, coordinates step-level queue sequencing, tracks worker leases, and serves execution telemetry to the dashboard. 

The backend **never executes user business logic**, nor does it store sensitive API credentials or model keys. All workflow execution occurs locally on developer workers.

---

## 🛠️ Technology Stack & Architecture Specifications

| Component | Technology | Version Constraint | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | `>= 3.12` | High-performance asynchronous runtime. |
| **Framework** | FastAPI | `>= 0.110.0` | Asynchronous REST API & OpenAPI schema generator. |
| **ORM** | SQLAlchemy (Async) | `>= 2.0.0` | Non-blocking database models & query builder (`sqlalchemy[asyncio]`). |
| **Driver** | AsyncPG | `>= 0.30.0` | High-throughput PostgreSQL database driver. |
| **Config** | Pydantic Settings | `>= 2.0.0` | Type-safe environment configuration loader. |
| **Validation** | Pydantic | `>= 2.7.0` | Request serialization & payload schema validation. |
| **Security** | PyJWT | `>= 2.8.0` | Dashboard Supabase Bearer JWT decoding & validation. |

---

## 🏗️ Architecture & Component Layers (Hexagonal / Ports & Adapters)

The backend follows **Hexagonal Architecture (Ports & Adapters)** to decouple core workflow domain logic from infrastructure integrations:

```text
  [ Dashboard UI (Next.js) ]          [ SDK Worker Instances ]
             │                                   │
             ▼ (Bearer JWT)                      ▼ (X-ApexFlow-Project-Key)
    ┌──────────────────────────────────────────────────────────────────┐
    │                     FastAPI API Router Layer                     │
    │        (workflows.py, steps.py, storage.py, keys.py, health.py)  │
    └────────────────┬─────────────────────────────────────────────────┘
                                     │
                                     ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │                      Service Engine Layer                        │
    │       (WorkflowService, StepService, QueueService, etc)          │
    └─────────────────┬──────────────────────────────┬─────────────────┘
                      │                              │
                      ▼                              ▼
    ┌──────────────────────────────────┐   ┌───────────────────────────┐
    │   Infrastructure Adapters Layer  │   │  Async SQLAlchemy ORM     │
    │    (`app/adapters/storage/`)     │   │   & PostgreSQL Database   │
    │  - LocalStorage (Atomic Disk)    │   │  (WorkflowRuns, Steps)    │
    │  - S3Storage (Supabase/S3/R2)    │   │                           │
    │  - PayloadPolicyManager (250KB)  │   │                           │
    └──────────────────────────────────┘   └───────────────────────────┘
```

### 🧱 Services vs. Adapters Design Pattern
- **Services Layer (`app/services/`)**: Contains pure business logic and orchestrates domain entities (`WorkflowRun`, `WorkflowStep`, `ProjectKey`). It remains independent of third-party cloud SDKs or file storage mechanisms.
- **Adapters Layer (`app/adapters/`)**: Implements infrastructure contracts ("Ports") to connect external systems to the control plane.
  - **Implemented Adapters**:
    - `adapters/storage/base.py`: `BaseStorageAdapter` interface (`save`, `get`, `exists`, `delete`).
    - `adapters/storage/local_adapter.py`: `LocalStorageAdapter` with atomic disk writes (`write` + `os.fsync` + `os.replace`), path traversal protection, and 2MB single payload ceiling enforcement.
    - `adapters/storage/s3_adapter.py`: `S3StorageAdapter` supporting Supabase S3, AWS S3, MinIO, and Cloudflare R2 via `boto3`.
    - `adapters/storage/policy.py`: `PayloadPolicyManager` enforcing 250KB inline offload threshold and `$apexflow_ref` creation.

---

## ⚡ Core Engine Architecture & Resilience Mechanisms

### 1. Database Connection Pooling & Fault Recovery
The database engine (`app/core/database.py`) is engineered for production stability under heavy concurrency and transient network drops:
- **`pool_pre_ping=True`**: Tests connections before usage to automatically drop and replace stale/dead connections.
- **`pool_recycle=1800`**: Recycles database connections every 30 minutes to prevent firewall or PostgreSQL server-side connection timeout drops.
- **Connection Pool Tuning**: Configures `pool_size=20` and `max_overflow=10` for high concurrency without PostgreSQL connection exhaustion.

### 2. High-Throughput Scoped Queue Polling & Scheduling (`QueueService`)
- Uses dialect-aware PostgreSQL `SELECT FOR UPDATE OF WorkflowStep SKIP LOCKED`.
- **Scheduled & Priority Dequeuing**: Filters steps by `available_at <= now()` and orders queue pickup by `priority ASC, available_at ASC, created_at ASC`, ensuring high-priority steps run first while respecting delayed step schedules.
- **Lease & Timeout Recovery**:
  - `recover_stale_locks`: Automatically recovers stale step leases (`locked_until < now()`) when worker nodes crash.
  - `recover_timed_out_workflows`: Detects workflow runs exceeding `deadline_at` (`timeout_seconds`), transitions the run to `failed`, and cancels pending/running child steps.

### 3. Cascading Parent-Child Workflow Lifecycle (`WorkflowService`)
The backend provides automatic sub-tree lifecycle management for hierarchical workflows:
- **Parent Cancellation Cascade**: Cancelling a parent workflow run (`cancel_workflow_run`) automatically updates active child sub-workflows (`parent_workflow_id == workflow_run_id` in `pending`/`running`) to `cancelled`.
- **Parent Restart Cascade**: Restarting a parent workflow run (`restart_workflow_run`) automatically resets failed or cancelled child sub-workflows back to `pending`.
- **In-Memory ORM Synchronization**: Updates both in-memory model instances and database rows during lifecycle mutations to ensure consistent API responses.

### 4. Large Payload Offloading & Storage Architecture
To maintain database performance and prevent `jsonb` table bloat:
- **Small Payloads ($\le 250\text{ KB}$)**: Stored inline directly in PostgreSQL `jsonb`.
- **Offloaded Payloads ($> 250\text{ KB}$ up to $2\text{ MB}$)**: Offloaded to object storage (Supabase S3 / AWS S3 / R2) or local storage directory (`.apexflow_storage/`).
- **DB Reference Descriptor (`$apexflow_ref`)**: Offloaded payloads in `jsonb` are replaced with a canonical pointer descriptor:
  ```json
  {
    "$apexflow_ref": true,
    "key": "payloads/20261005_abcdef123.json",
    "size_bytes": 1048576,
    "content_type": "application/json",
    "provider": "s3",
    "encrypted": false,
    "created_at": "2026-10-05T19:00:00Z"
  }
  ```
- **Zero-Knowledge Ciphertext Envelopes**: When client-side AES-256-GCM encryption is used, the control plane flags `encrypted: true` in the storage descriptor without holding or needing decryption keys.
- **Pass-by-Reference ($> 2\text{ MB}$)**: Payloads exceeding the 2MB control-plane ceiling are rejected with `HTTP 413 Payload Too Large`. Users pass S3 URIs (`s3://...`) directly in step parameters.

### 5. Server-Scheduled Retries & Flow Control
- **Exponential Backoff**: When a step reports a retryable failure, the control plane calculates exponential backoff:
  $$T_{\text{delay}} = 2^{\text{attempt}-1} \text{ seconds}$$
  and sets `available_at = now() + T_{\text{delay}}` (or honors explicit `retry_delay_seconds`), persisting retry state durably in PostgreSQL even if the worker dies.
- **Step Execution Delays (`delay_seconds`)**: Steps can specify initial dispatch delays before becoming visible to dequeuers.

### 6. Time-Travel Debugging via Workflow Forking (`WorkflowService`)
- Developers can branch a new workflow from any point in an existing run (`POST /api/v1/workflows/{id}/fork?from_step=N`).
- Prior step outputs ($1 \dots N-1$) are cloned and memoized into the new run. Step $N$ is placed into `queued` state for execution.
- Lineage is preserved via `forked_from_id`, enabling auditability and iterative local debugging of production failures.

### 7. Trigger Debouncing & Event Coalescing
- High-frequency triggers sharing a `deduplication_id` can specify `debounce_seconds` (and optional `max_debounce_seconds`).
- Subsequent events arriving within the window merge metadata and extend `debounced_until` (capped at `debounce_deadline_at`), executing the workflow once when quiet.

### 8. Database Retention Strategy (`pg-cron`)
To prevent database storage bloating on PostgreSQL databases:
- **Soft Payload Pruning** (`prune_old_payloads`): Daily at 02:00 AM UTC, clears JSON payloads (`{}`) for completed runs older than 7 days, reducing disk usage by 90%+ while preserving run telemetry metrics for 30 days.
- **Hard Batched Delete** (`prune_old_workflow_runs_batched`): Daily at 03:00 AM UTC, deletes terminal runs older than 30 days in non-blocking batches of 2,000 rows.
- Cloud Object Storage lifecycle retention (auto-deleting expired objects) is managed natively via S3 bucket lifecycle rules.

---

## ⚙️ Storage Configuration Settings

Storage settings are configured in `app/core/config.py` via environment variables (`.env`):

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PAYLOAD_MAX_INLINE_BYTES` | `int` | `256000` (250 KB) | Threshold size in bytes before offloading payload. |
| `PAYLOAD_MAX_SINGLE_BYTES` | `int` | `2097152` (2 MB) | Maximum single payload size ceiling allowed by control plane API. |
| `STORAGE_PROVIDER` | `str` | `"local"` | Storage provider: `"local"` or `"s3"`. |
| `STORAGE_LOCAL_DIR` | `str` | `".apexflow_storage"` | Directory path for local volume storage fallback. |
| `S3_BUCKET_NAME` | `str` | `None` | Target S3 / Supabase bucket name. |
| `S3_ENDPOINT_URL` | `str` | `None` | Endpoint URL for Supabase S3, MinIO, or Cloudflare R2. |
| `AWS_ACCESS_KEY_ID` | `str` | `None` | S3 / Supabase Access Key ID. |
| `AWS_SECRET_ACCESS_KEY` | `str` | `None` | S3 / Supabase Secret Access Key. |
| `AWS_REGION` | `str` | `"us-east-1"` | AWS Region name. |

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
| `/api/v1/workflows` | `POST` | Project API Key | Create, debounced buffer, or deduplicate a workflow run execution state. |
| `/api/v1/workflows` | `GET` | Bearer / Key | List workflow runs (paginated & filtered). |
| `/api/v1/workflows/{id}` | `GET` | Bearer / Key | Fetch workflow run detail and ordered step execution timeline. |
| `/api/v1/workflows/{id}/fork` | `POST` | Bearer / Key | Fork workflow from step $N$ with prior checkpoints memoized. |
| `/api/v1/workflows/{id}/complete` | `POST` | Project API Key | Mark workflow run completed upon SDK function completion. |
| `/api/v1/workflows/{id}/cancel` | `POST` | Bearer / Key | Cancel active workflow run and mark queued steps cancelled. |
| `/api/v1/workflows/{id}/restart` | `POST` | Bearer / Key | Reset failed/cancelled steps to queued and restart run. |
| `/api/v1/steps` | `POST` | Project API Key | Queue a new step under a workflow run (with optional delay & priority). |
| `/api/v1/steps/poll` | `POST` | Project API Key | Poll next queued step using `FOR UPDATE SKIP LOCKED` (priority & available_at). |
| `/api/v1/steps/report` | `POST` | Project API Key | Report worker step execution result (`success` / `failed`). |
| `/api/v1/storage/upload` | `POST` | Project API Key | Upload payload/file artifact and return `$apexflow_ref` descriptor. |
| `/api/v1/storage/download/{key:path}` | `GET` | Bearer / Key | Stream binary content or offloaded JSON for a storage key. |
