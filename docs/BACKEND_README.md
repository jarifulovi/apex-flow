# ApexFlow Backend Control Plane (`apex-flow-backend`)

> **Asynchronous REST API State Coordinator, Database Queue Engine, and Execution Telemetry Provider.**

---

## 📌 Description

The **ApexFlow Backend Control Plane** manages workflow execution states, coordinates step-level queue sequencing via PostgreSQL, and processes worker status handshakes without executing user business logic or storing sensitive API credentials.

---

## 🛠️ Technology Stack & Dependency Specifications

| Component | Technology | Version Constraint | Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | `>= 3.12` | High-performance asynchronous runtime. |
| **Framework** | FastAPI | `>= 0.136.0, < 0.142.0` | Asynchronous REST API & OpenAPI docs generator. |
| **ORM** | SQLAlchemy (Async) | `>= 2.0.0` | Async database models & query builder (`sqlalchemy[asyncio]`). |
| **Driver** | AsyncPG | `>= 0.30.0` | Non-blocking PostgreSQL database driver. |
| **Concurrency** | Greenlet | `>= 3.0.0` | Required for SQLAlchemy async greenlet context switching. |
| **Config** | Pydantic Settings | `>= 2.0.0` | Type-safe environment configuration loader. |
| **Validation** | Pydantic | `>= 2.7.0` | Data serialization & request schema validation. |
| **Security** | PyJWT | `>= 2.8.0` | JWT token decoding & validation (`pyjwt[crypto]`). |
| **Migrations** | Alembic | `>= 1.13.0` | Database schema migration engine. |
| **Testing** | Pytest & Pytest-Asyncio | `>= 8.0.0` | Async automated integration & unit test suite. |

---

## 🏗️ Architecture & Component Layers

```text
[ HTTP Client / Worker / Dashboard ]
                 │
                 ▼
     ┌──────────────────────┐
     │   app/api/v1/        │  <-- Thin HTTP Routers (workflows.py, steps.py, health.py)
     └───────────┬──────────┘
                 │
                 ▼
     ┌──────────────────────┐
     │   app/services/      │  <-- Business Logic & Queue Engine (StepService, WorkflowService)
     └───────────┬──────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
 ┌──────────────┐  ┌──────────────┐
 │ app/models/  │  │ app/schemas/ │  <-- SQLAlchemy ORM Models & Pydantic Schemas
 └──────┬───────┘  └──────────────┘
        │
        ▼
 ┌──────────────┐
 │  app/core/   │  <-- Infrastructure (config.py, database.py, exceptions.py)
 └──────┬───────┘
        │
        ▼
 ┌──────────────────────────┐
 │ PostgreSQL / Supabase DB │  <-- Relational Persistence & Row-Locking Queue
 └──────────────────────────┘
```

---

## 🔄 Short Data Flow

1. **Initiate**: `POST /api/v1/workflows` creates a `workflows` record with `status = 'pending'`.
2. **Queue**: `POST /api/v1/steps` creates `workflow_steps` records with `status = 'queued'`.
3. **Dispatch**: `POST /api/v1/steps/poll` uses **PostgreSQL `FOR UPDATE SKIP LOCKED`** to acquire the next queued step, setting `status = 'running'` and `attempt_count += 1`.
4. **Report**: Worker executes locally and posts `POST /api/v1/steps/report` with `status = 'success'` or `'failed'`.
5. **Evaluate**: Backend updates step status, checks remaining active steps, and auto-completes parent workflow (`status = 'completed'`).

---

## 🗄️ Database Schemas

### 1. `project_keys` Table
Stores hashed API project keys for SDK/Worker authentication.

```sql
CREATE TABLE project_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    last_used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Performance index for SHA-256 API key authentication lookup
CREATE INDEX idx_project_keys_hash ON project_keys (key_hash) WHERE status = 'active';
```

### 2. `workflows` Table
Tracks master execution states per tenant/user.

```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3. `workflow_steps` Table
Acts as step execution log and concurrency-safe distributed queue.

```sql
CREATE TABLE workflow_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Performance Index for SKIP LOCKED queue polling queries
CREATE INDEX idx_workflow_steps_queue ON workflow_steps (status, created_at);
```

---

## 🔒 Authentication & Security Layer

The backend control plane enforces a **Two-Dependency Authentication Model** (`app/api/deps.py`):

1. **`get_current_user_from_api_key`**: 
   - Used by SDK/Worker routes (`/api/v1/workflows`, `/api/v1/steps`).
   - Validates the `X-ApexFlow-Project-Key` header against stored SHA-256 hashes in `project_keys`.
   - Automatically scopes workflow queueing, step polling, and status reporting to the key's owner (`user_id`).

2. **`get_current_user_from_jwt`**:
   - Used by Dashboard UI routes (`/api/v1/keys`).
   - Decodes Supabase Bearer JWT tokens in the `Authorization` header (`sub` claim).

---

## 🔌 API Endpoints Summary

| Endpoint | Method | Auth Dependency | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | None | Zero-DB liveness probe for cloud health checks. |
| `/api/v1/health/db` | `GET` | None | Readiness probe checking live PostgreSQL ping. |
| `/api/v1/keys` | `POST` | Supabase JWT | Create a new project API key (`raw_key` shown once). |
| `/api/v1/keys` | `GET` | Supabase JWT | List user's active & revoked project API keys. |
| `/api/v1/keys/{key_id}` | `DELETE` | Supabase JWT | Revoke a project API key by ID. |
| `/api/v1/workflows` | `POST` | API Key | Create a new workflow run execution state. |
| `/api/v1/workflows` | `GET` | API Key | List tenant workflows (paginated, user scoped). |
| `/api/v1/workflows/{id}` | `GET` | API Key | Fetch workflow run details & step timeline history. |
| `/api/v1/steps` | `POST` | API Key | Queue a new execution step under a workflow. |
| `/api/v1/steps/poll` | `POST` | API Key | Poll tenant's next queued step via `FOR UPDATE SKIP LOCKED`. |
| `/api/v1/steps/report` | `POST` | API Key | Report worker step status (`success`/`failed`). |

