import {
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import type { WorkflowStep } from "../data";

const STATUS_CONFIG: Record<
  WorkflowStep["status"],
  { label: string; className: string; dot: string; icon: React.ElementType }
> = {
  queued:  { label: "Queued",  className: "status-badge status-badge--pending",   dot: "status-dot--pending",   icon: Clock },
  running: { label: "Running", className: "status-badge status-badge--running",   dot: "status-dot--running",   icon: Loader2 },
  success: { label: "Success", className: "status-badge status-badge--completed", dot: "status-dot--completed", icon: CheckCircle2 },
  failed:  { label: "Failed",  className: "status-badge status-badge--failed",    dot: "status-dot--failed",    icon: AlertTriangle },
};

import React, { useState } from "react";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function PayloadCell({ payload }: { payload: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const isEmpty = Object.keys(payload).length === 0;
  if (isEmpty) return <span className="table-date">—</span>;
  return (
    <div className="payload-cell">
      <button
        className="payload-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span>payload</span>
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
      </button>
      {open && (
        <pre className="payload-json">
          {JSON.stringify(payload, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function StepsTable({ steps }: { steps: WorkflowStep[] }) {
  if (steps.length === 0) {
    return (
      <div className="table-empty">
        <CheckCircle2 size={28} className="table-empty-icon" />
        <p className="table-empty-text">No steps found</p>
        <p className="table-empty-sub">Steps created by your workflows will appear here.</p>
      </div>
    );
  }

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Step</th>
            <th>Workflow</th>
            <th>Status</th>
            <th>Attempts</th>
            <th>Output</th>
            <th>Error</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step) => {
            const cfg = STATUS_CONFIG[step.status];
            const Icon = cfg.icon;
            return (
              <tr key={step.id}>
                <td>
                  <div className="table-cell-primary">
                    <div className={`table-icon ${step.status === "failed" ? "table-icon--red" : step.status === "success" ? "table-icon--emerald" : "table-icon--violet"}`}>
                      <Icon size={13} className={step.status === "running" ? "animate-spin" : ""} />
                    </div>
                    <p className="table-name">{step.step_name}</p>
                  </div>
                </td>
                <td>
                  <span className="table-meta">{step.workflow_name ?? step.workflow_id.slice(0, 8)}</span>
                </td>
                <td>
                  <span className={cfg.className}>
                    <span className={`status-dot ${cfg.dot}`} />
                    {cfg.label}
                  </span>
                </td>
                <td>
                  <span className="table-steps">{step.attempt_count}</span>
                </td>
                <td>
                  <PayloadCell payload={step.output_payload} />
                </td>
                <td>
                  {step.error_message ? (
                    <span className="table-error" title={step.error_message}>
                      {step.error_message.slice(0, 40)}…
                    </span>
                  ) : (
                    <span className="table-date">—</span>
                  )}
                </td>
                <td>
                  <span className="table-date">{formatDate(step.updated_at)}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
