# ApexFlow Observability Dashboard (`apex-flow-dashboard`)

> **Real-Time Telemetry, Workflow Execution Monitoring, and Interactive Control Platform built with Next.js 14, Tailwind CSS, & Radix UI.**

---

## 📌 Overview

The **ApexFlow Observability Dashboard** provides real-time visibility into workflow execution runs, step execution timelines, worker heartbeats, and payload inspection.

---

## ✨ Features & Capabilities

- 🖥️ **Console Shell Architecture**: Streamlined console layout with collapsible `Sidebar` navigation, integrated `TopBar` breadcrumbs, project tenant switcher, and contextual refresh controls.
- 📂 **Nested Workflow Navigation**:
  - **Definitions Catalog** (`/dashboard/workflows`): Aggregated overview of all unique workflow pipelines with total runs, success rates, active/failed runs, and duration metrics.
  - **Definition Runs View** (`/dashboard/workflows/[name]`): Filterable run execution history dedicated to a specific workflow definition.
  - **Run Detail & Step Timeline** (`/dashboard/workflows/[name]/[id]`): In-depth execution telemetry with sequential step timelines, attempt counts, execution duration, and time-travel forking.
- 📦 **Payload Offload Inspector (`PayloadViewerModal`)**: Automatically detects offloaded storage descriptors (`$apexflow_ref`), displays telemetry badges (`[ 📦 Offloaded Storage (698.9 KB) | LOCAL/S3 ]`), and provides a one-click **Download Payload** button alongside formatted JSON preview.
- 🔍 **Error Inspector Modal**: Visualizes runtime exceptions, error messages, and full diagnostic stack tracebacks for failed steps.
- ⚡ **Interactive Control Actions**: Trigger workflow runs, cancel active runs, and restart failed/cancelled runs with one click.
- 🔑 **Project Key Management**: Generate and manage SHA-256 hashed API keys (`af_live_...`).

---

## 🚀 Getting Started

```bash
# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 TypeScript Compilation Verification

```bash
npx tsc --noEmit
```
