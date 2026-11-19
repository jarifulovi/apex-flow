# ApexFlow Observability Dashboard (`apex-flow-dashboard`)

> **Real-Time Telemetry, Workflow Execution Monitoring, and Interactive Control Platform built with Next.js 16, Tailwind CSS, & Radix UI.**

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
- ⏰ **Cron & Scheduled Workflows (`/dashboard/workflows?tab=schedules`)**: View and manage recurring cron schedules with human-readable translations, live next-run countdowns, IANA timezone selection, pause/resume toggles, and one-click **Run Now** execution.
- 📦 **Payload Offload Inspector (`PayloadViewerModal`)**: Automatically detects offloaded storage descriptors (`$apexflow_ref`), displays telemetry badges (`[ 📦 Offloaded Storage (698.9 KB) | LOCAL/S3 ]`), and provides a one-click **Download Payload** button alongside formatted JSON preview.
- 🔍 **Error Inspector Modal**: Visualizes runtime exceptions, error messages, and full diagnostic stack tracebacks for failed steps.
- ⚡ **Interactive Control Actions**: Trigger workflow runs, cancel active runs, and restart failed/cancelled runs with one click.
- 🔑 **Project Key Management**: Generate and manage SHA-256 hashed API keys (`af_live_...`).
- 🔔 **Multi-Channel Alerting & Webhooks (`/dashboard/settings`)**: Configure Slack, Discord, or custom HTTP webhooks with provider auto-detection, failure event toggles (`workflow.failed`, `workflow.timed_out`, `step.max_retries_exhausted`, `worker.disconnected`), sliding-window rate limiting presets, and live connection test verification.
- ⚙️ **Project Maintenance & Data Purging**: Update project name, trigger instant deletion of finished execution runs/logs with the **Purge Completed & Failed Runs** action, and handle project deletion.

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
