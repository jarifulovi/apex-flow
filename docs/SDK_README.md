# ApexFlow Multi-Language SDK Specification (`docs/SDK_README.md`)

> **Language-Agnostic SDK Architecture, Execution Mechanics, Client Responsibilities, and Protocol Specifications.**

---

## 📌 Overview & Core Concerns

An **ApexFlow SDK** is a client library operating on developer worker infrastructure. It allows developers to write stateful, multi-step workflow pipelines using native language primitives (`async/await`, functions, classes, decorators, goroutines).

The SDK is **not merely a thin HTTP wrapper** for the control plane. It encapsulates vital execution concerns including local state memoization, durable crash recovery, exponential backoff retries, signal handling, and status reporting.

---

## ⚙️ Key SDK Concerns & Responsibilities

```text
       ┌─────────────────────────────────────────────────────────────┐
       │                    SDK Worker Runtime                       │
       │                                                             │
       │  ┌───────────────────┐             ┌─────────────────────┐  │
       │  │ Durable           │             │ Resilient Retry &   │  │
       │  │ Checkpointing     │             │ Error Classification│  │
       │  └─────────┬─────────┘             └──────────┬──────────┘  │
       │            │                                  │             │
       │            ▼                                  ▼             │
       │  ┌───────────────────┐             ┌─────────────────────┐  │
       │  │ Step Order        │             │ Signal Handling &   │  │
       │  │ Sequencing        │             │ Graceful Shutdown   │  │
       │  └─────────┬─────────┘             └──────────┬──────────┘  │
       └────────────┼──────────────────────────────────┼─────────────┘
                    │                                  │
                    ▼                                  ▼
       ┌─────────────────────────────────────────────────────────────┐
       │             ApexFlow Control Plane REST API                 │
       └─────────────────────────────────────────────────────────────┘
```

### 1. Durable Checkpointing & Execution Resumption
- Before executing a step, the SDK queries the control plane or local memory for existing execution checkpoints.
- If a step was successfully executed during a prior attempt, the SDK **skips re-executing the step function** and immediately returns the memoized result.
- If a worker crashes on Step 3 of a 5-step pipeline, a new worker instance resuming the workflow skips Steps 1 and 2 automatically, resuming execution directly at Step 3.

### 2. Resilient Local Retries & Error Classification
- Executes step functions with configurable retry limits and exponential backoff.
- **Silent API Error Detection**: Inspects raw third-party HTTP/JSON API responses (`{"success": false}`) and converts silent failures into retryable exceptions.
- **Immediate Abort on Non-Retryable Errors**: Immediately aborts remaining retry attempts when encountering non-transient failures (such as `401 Unauthorized`, `400 Bad Request`, or `OUT_OF_STOCK`), marking the step failed without wasting retry budgets.

### 3. Explicit Top-Level Workflow Completion
- Rather than forcing the control plane to guess when dynamic workflows finish, the SDK sends an explicit completion signal (`POST /api/v1/workflows/{id}/complete`) when the top-level workflow function finishes execution.

### 4. Idempotency & Sub-Workflow Propagation
- **Deduplication Transmission**: Accepts `deduplication_id` on workflow triggers to guarantee single-execution idempotency at the database level.
- **Parent-Child Lineage**: Propagates `parent_workflow_id` when launching child workflows to preserve execution tree lineage in monitoring dashboards.

### 5. Deterministic Step Sequence Tracking
- Automatically assigns an incrementing sequence integer (`step_order = 1, 2, 3...`) when queueing steps under a workflow run, ensuring deterministic step ordering in timelines regardless of microsecond database timestamp precision.

### 6. Signal Handling & Graceful Shutdown
- Catches system termination signals (`SIGINT`, `SIGTERM`).
- Completes currently executing in-flight step functions, notifies the control plane, and deregisters worker heartbeats before terminating process execution cleanly.

### 7. Transparent Large Payload Offloading & Pointer Resolution (`$apexflow_ref`)
- Small JSON payloads ($\le 250\text{ KB}$) are transmitted directly to control plane API endpoints in inline JSON format.
- Large JSON dictionaries or binary file payloads ($> 250\text{ KB}$) are transparently uploaded by the SDK (`StorageResolver`) via `POST /api/v1/storage/upload` before step registration or status reporting.
- The SDK replaces large payloads with a lightweight `$apexflow_ref` pointer descriptor:
  ```json
  {
    "$apexflow_ref": true,
    "key": "payloads/20261005_abcdef123.json",
    "size_bytes": 1048576,
    "content_type": "application/json",
    "provider": "local"
  }
  ```
- When acquiring steps or loading step checkpoints, the SDK transparently dereferences `$apexflow_ref` pointers back into native dictionaries or bytes via `GET /api/v1/storage/download/{key}`, ensuring developer step code never needs explicit S3 API logic.

---

## 🌐 Control Plane REST Protocol

All language SDKs communicate with the backend control plane via HTTP REST endpoints authenticated via `X-ApexFlow-Project-Key: af_live_...`:

```text
[ Developer Worker SDK ] ──(HTTP REST with X-ApexFlow-Project-Key)──> [ ApexFlow Control Plane ]
```

### Protocol Interaction Map:

1. **Trigger Workflow**: `POST /api/v1/workflows`
   - *Payload*: `{"workflow_name": "<name>", "metadata": {...}, "deduplication_id": "...", "parent_workflow_id": "..."}`
   - *Returns*: Workflow run metadata (`id`, `status`).

2. **Queue Step**: `POST /api/v1/steps`
   - *Payload*: `{"workflow_id": "<uuid>", "step_name": "<name>", "step_order": 1, "input_payload": {...}}`
   - *Returns*: Queued step metadata (`id`, `status`).

3. **Poll Step**: `POST /api/v1/steps/poll`
   - *Payload*: `{"worker_name": "...", "worker_id": "...", "step_names": [...]}`
   - *Returns*: Next available step payload or `204 No Content`.

4. **Report Step Status**: `POST /api/v1/steps/report`
   - *Payload*: `{"step_id": "<uuid>", "status": "success" | "failed", "output_payload": {...}, "error_message": "..."}`
   - *Returns*: Updated step status.

5. **Complete Workflow**: `POST /api/v1/workflows/{id}/complete`
   - *Returns*: Final workflow status (`completed`).

---

## 📁 Multi-Language SDK Directory Layout

All language SDK implementations reside under `sdks/` in the monorepo:

- **Python**: `sdks/python/` (`apex-flow-sdk`)
- **TypeScript**: `sdks/typescript/` (`@apex-flow/sdk`)
- **Go**: `sdks/go/` (`github.com/apex-flow/sdk-go`)
- **Java**: `sdks/java/`
