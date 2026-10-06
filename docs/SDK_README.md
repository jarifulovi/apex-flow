# ApexFlow Multi-Language SDK Specification (`docs/SDK_README.md`)

> **Language-Agnostic SDK Architecture, Execution Mechanics, Client Responsibilities, and Protocol Specifications.**

---

## 📌 Overview & Core Concerns

An **ApexFlow SDK** is a client library operating on developer worker infrastructure. It allows developers to write stateful, multi-step workflow pipelines using native language primitives (`async/await`, functions, classes, decorators, goroutines).

The SDK is **not merely a thin HTTP wrapper** for the control plane. It encapsulates vital execution concerns including local state memoization, durable crash recovery, exponential backoff retries with full jitter, signal handling, step execution isolation, and status reporting.

---

## ⚙️ Key SDK Concerns & Responsibilities

```text
       ┌─────────────────────────────────────────────────────────────┐
       │                    SDK Worker Runtime                       │
       │                                                             │
       │  ┌───────────────────┐             ┌─────────────────────┐  │
       │  │ Durable           │             │ Resilient Retry &   │  │
       │  │ Checkpointing     │             │ Full Jitter Backoff │  │
       │  └─────────┬─────────┘             └──────────┬──────────┘  │
       │            │                                  │             │
       │            ▼                                  ▼             │
       │  ┌───────────────────┐             ┌─────────────────────┐  │
       │  │ Async Callable    │             │ Worker Step Error   │  │
       │  │ & Class Support   │             │ Isolation Engine    │  │
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

### 2. Resilient Network HTTP Client & Full Jitter Backoff
- All SDK network requests (`trigger_workflow`, `complete_workflow`, `report_step`, `poll_next_step`, `upload_payload`, `download_payload`) execute through a resilient HTTP wrapper (`_request_with_retry`).
- **Automatic Retries**: Automatically retries transient network connection drops, timeouts, and HTTP server errors (`500`, `502`, `503`, `504`).
- **Exponential Backoff & Full Jitter**:
  $$T_{\text{wait}} = \min(T_{\text{max}}, T_{\text{base}} \times 2^{\text{attempt}}) \times \text{random}(0.8, 1.2)$$
- **Worker Loop Survivability**: If the Control Plane or local network drops temporarily, worker polling loops do not crash. Workers enter a degraded retry backoff state and reconnect seamlessly when the network returns online.

### 3. Support for Async Functions, Callables & Class Instances
- Evaluates step functions using flexible async introspection (`asyncio.iscoroutinefunction`, `inspect.iscoroutinefunction`, and `inspect.iscoroutinefunction(getattr(fn, "__call__", None))`).
- Seamlessly handles standard `async def` functions, synchronous functions, and callable class instances (such as simulation step objects).

### 4. Worker Step Execution Exception Isolation
- Step function execution inside worker polling loops is wrapped in an isolated execution sandbox.
- If a step function raises an exception during execution (e.g. API failure, database timeout, or custom error), the worker catches it cleanly and reports the failure (`status: "failed"`, `error_message`, and `attempt_count`) back to `/api/v1/steps/report`.
- This ensures worker polling loops stay alive while allowing the Control Plane to track step attempt counts and trigger retry policies.

### 5. Explicit Top-Level Workflow Completion
- Rather than forcing the control plane to guess when dynamic workflows finish, the SDK sends an explicit completion signal (`POST /api/v1/workflows/{id}/complete`) when the top-level workflow function finishes execution.

### 6. Idempotency & Sub-Workflow Propagation
- **Deduplication Transmission**: Accepts `deduplication_id` on workflow triggers to guarantee single-execution idempotency at the database level.
- **Parent-Child Lineage**: Automatically attaches `parent_workflow_id` when launching sub-workflows from within workflow context (`ctx.trigger_workflow`), establishing hierarchical lineage in monitoring dashboards.

### 7. Deterministic Step Sequence Tracking
- Automatically assigns an incrementing sequence integer (`step_order = 1, 2, 3...`) when queueing steps under a workflow run, ensuring deterministic step ordering in timelines regardless of microsecond database timestamp precision.

### 8. Signal Handling & Graceful Shutdown
- Catches system termination signals (`SIGINT`, `SIGTERM`).
- Completes currently executing in-flight step functions, notifies the control plane, and deregisters worker heartbeats before terminating process execution cleanly.

### 9. Transparent Large Payload Offloading & Pointer Resolution (`$apexflow_ref`)
- Small JSON payloads ($\le 250\text{ KB}$) are transmitted directly to control plane API endpoints in inline JSON format.
- Large JSON dictionaries or binary file payloads ($> 250\text{ KB}$) are transparently offloaded by the SDK (`StorageResolver`) via `POST /api/v1/storage/upload` before step registration or status reporting.
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
