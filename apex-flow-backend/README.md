# ApexFlow Backend Control Plane (`apex-flow-backend`)

> **Asynchronous REST API State Coordinator, High-Throughput Queue Engine, and Execution Telemetry Provider.**

---

## 📌 Quickstart

```bash
# Start backend control plane with hot reloading
./dev.sh
```
- **Control Plane API**: `http://127.0.0.1:8000`
- **Swagger Documentation**: `http://127.0.0.1:8000/docs`

---

## 🏗️ Architecture & Component Layers

ApexFlow Backend uses **Hexagonal Architecture (Ports & Adapters)** to isolate business logic from infrastructure implementations:

- **`app/services/`**: Core domain logic (`WorkflowService`, `StepService`, `QueueService`).
- **`app/adapters/`**: External infrastructure integrations (`adapters/storage/` with Local Volume & S3 adapters).

> 📘 **Detailed Architecture & API Specifications**: Please see [docs/BACKEND_README.md](../docs/BACKEND_README.md) for full endpoint specifications, Ports & Adapters architecture, 250KB payload threshold offloading, and database retention policies.
