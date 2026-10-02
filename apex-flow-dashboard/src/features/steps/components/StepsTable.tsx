import React, { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronRight,
  Timer,
  Lock,
} from "lucide-react";
import type { WorkflowStep } from "@/features/steps/api";
import { formatDurationMs } from "@/features/workflows/api";

const STATUS_CONFIG: Record<
  WorkflowStep["status"],
  { label: string; className: string; dot: string; icon: React.ElementType }
> = {
  queued:  { label: "Queued",  className: "status-badge status-badge--pending",   dot: "status-dot--pending",   icon: Clock },
  running: { label: "Running", className: "status-badge status-badge--running",   dot: "status-dot--running",   icon: Loader2 },
  success: { label: "Success", className: "status-badge status-badge--completed", dot: "status-dot--completed", icon: CheckCircle2 },
  failed:  { label: "Failed",  className: "status-badge status-badge--failed",    dot: "status-dot--failed",    icon: AlertTriangle },
};

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
  const isEmpty = !payload || Object.keys(payload).length === 0;
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
            <th>Step Name</th>
            <th>Workflow Run</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Attempts</th>
            <th>Output</th>
            <th>Error</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step) => {
            const cfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.queued;
            const Icon = cfg.icon;
            const wfRunId = step.workflow_run_id || (step as any).workflow_id || "";
            const duration = formatDurationMs(step.started_at || step.created_at, step.completed_at);
            const isLocked = step.locked_until && new Date(step.locked_until).getTime() > Date.now();

            return (
              <tr key={step.id}>
                <td>
                  <div className="table-cell-primary">
                    <div className={`table-icon ${step.status === "failed" ? "table-icon--red" : step.status === "success" ? "table-icon--emerald" : "table-icon--violet"}`}>
                      <Icon size={13} className={step.status === "running" ? "animate-spin" : ""} />
                    </div>
                    <div>
                      <p className="table-name font-mono">{step.step_name}</p>
                      {isLocked && (
                        <span className="text-[10px] text-amber-400 font-mono flex items-center gap-1">
                          <Lock size={10} /> Locked by worker
                        </span>
                      )}
                    </div>
                  </div>
                </td>
                <td>
                  <Link
                    href={`/dashboard/workflows/${wfRunId}`}
                    className="table-meta font-mono hover:text-violet-300 underline underline-offset-2"
                  >
                    #{wfRunId.slice(0, 8)}
                  </Link>
                </td>
                <td>
                  <span className={cfg.className}>
                    <span className={`status-dot ${cfg.dot}`} />
                    {cfg.label}
                  </span>
                </td>
                <td>
                  <span className="flex items-center gap-1.5 text-xs text-zinc-300 font-mono">
                    <Timer size={12} className="text-zinc-500" />
                    {duration}
                  </span>
                </td>
                <td>
                  <span className="table-steps font-mono">
                    {step.attempt_count} / {step.max_attempts || 3}
                  </span>
                </td>
                <td>
                  <PayloadCell payload={step.output_payload} />
                </td>
                <td>
                  {step.error_message ? (
                    <span className="table-error" title={step.error_message}>
                      {step.error_message.slice(0, 35)}…
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
