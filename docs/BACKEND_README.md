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

### 1. `workflows` Table
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

### 2. `workflow_steps` Table
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

## 🔌 API Endpoints Summary

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/health` | `GET` | Zero-DB liveness probe for cloud health checks. |
| `/api/v1/health/db` | `GET` | Readiness probe checking live PostgreSQL ping. |
| `/api/v1/workflows` | `POST` | Create a new workflow run execution state. |
| `/api/v1/workflows` | `GET` | List workflows (paginated, user filterable). |
| `/api/v1/workflows/{id}` | `GET` | Fetch workflow run details & step timeline history. |
| `/api/v1/steps` | `POST` | Queue a new execution step under a workflow. |
| `/api/v1/steps/poll` | `POST` | Poll next queued step via `FOR UPDATE SKIP LOCKED`. |
| `/api/v1/steps/report` | `POST` | Report worker step execution status (`success`/`failed`). |
