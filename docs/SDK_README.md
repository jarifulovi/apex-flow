# ApexFlow Multi-Language SDK Specification (`docs/SDK_README.md`)

> **Language-Agnostic Client Library Specification, Control Plane Protocol, and Required SDK Capabilities.**

---

## 📌 Overview

An **ApexFlow SDK** is a client library running on the developer's local or hosted worker infrastructure. It enables developers to write stateful, multi-step workflows using native programming language constructs (`decorators`, `async/await`, `lambdas`, `goroutines`).

SDKs do not execute heavy logic on the ApexFlow Control Plane. Instead, they handle local step execution, exponential backoff retries, state memoization, and REST status reporting to the backend.

---

## 🌐 Control Plane Connection Protocol

All language SDKs communicate with the backend control plane via standard HTTP/1.1 or HTTP/2 JSON REST endpoints:

```text
[ Developer Worker SDK ] ──(HTTP REST)──> [ ApexFlow FastAPI Control Plane ]
```

### Protocol Interaction Flow:

1. **Triggering a Workflow**:
   - **Endpoint**: `POST /api/v1/workflows`
   - **Payload**: `{"user_id": "<uuid>", "metadata": {...}}`
   - **Purpose**: Initializes a master workflow execution run (`status = 'pending'`).

2. **Step Queue Registration**:
   - **Endpoint**: `POST /api/v1/steps`
   - **Payload**: `{"workflow_id": "<uuid>", "step_name": "<name>", "input_payload": {...}}`
   - **Purpose**: Registers a step in the control plane queue (`status = 'queued'`).

3. **Worker Queue Polling**:
   - **Endpoint**: `POST /api/v1/steps/poll`
   - **Header**: `X-ApexFlow-Project-Key: <key>`
   - **Purpose**: Worker polls for the next available queued step (dispatched via `FOR UPDATE SKIP LOCKED`).

4. **Step Execution Status Reporting**:
   - **Endpoint**: `POST /api/v1/steps/report`
   - **Payload**: `{"step_id": "<uuid>", "status": "success" | "failed", "output_payload": {...}, "error_message": "..."}`
   - **Purpose**: Reports local step execution completion or failure.

---

## 🧱 Required SDK Components & Architecture

Every ApexFlow language SDK (Python, TypeScript, Go, Java) must implement the following 5 core capabilities:

### 1. Client & Workflow Registry (`ApexFlowClient`)
- **Workflow Registration**: A mechanism (`@decorator`, method, or struct wrapper) to register named workflow functions.
- **Workflow Trigger**: Methods to launch workflow runs on the control plane.
- **Worker Polling Loop**: An asynchronous background loop that polls `POST /api/v1/steps/poll` and dispatches acquired steps to local execution handlers.

### 2. Execution Context (`WorkflowContext`)
Passed as the first argument into workflow functions to provide step execution primitives:
- `step(name, function, options)`: Wraps a single function call with durability.
- `parallel(step_list)`: Executes multiple independent steps concurrently.

### 3. Local State Memoization (Checkpointing)
- Before executing a step, the SDK checks its local execution cache (`step_cache`).
- If a step was already completed in a prior run attempt, the SDK skips re-execution and immediately returns the cached result.

### 4. Local Retry Engine & Backoff
- When a local step function throws an exception, the SDK catches the error and executes retries locally based on configured rules:
  - **Max Retries**: Default = 3.
  - **Exponential Backoff**: `sleep_time = backoff_factor ^ (attempt - 1)`.
  - **Non-Retryable Errors**: Immediate failure without retrying for bug errors (e.g. 400 Bad Request, 401 Unauthorized).

### 5. Secure Payload Offloading (The Pointer Pattern)
- Small JSON payloads (< 64KB) are transmitted directly in HTTP request bodies.
- Large binary or text outputs are uploaded by the SDK to Object Storage (S3 / Supabase Storage), sending only a secure URL pointer (`{"$pointer": "..."}`) to the control plane.

---

## 📁 Multi-Language SDK Folder Standard

All language SDKs reside under the `sdks/` directory in the monorepo:

- **Python**: `sdks/python/` (`apex-flow-sdk`)
- **TypeScript**: `sdks/typescript/` (`@apex-flow/sdk`)
- **Go**: `sdks/go/` (`github.com/apex-flow/sdk-go`)
- **Java**: `sdks/java/`
