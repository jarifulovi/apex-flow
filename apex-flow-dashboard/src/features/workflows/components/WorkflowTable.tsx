import { GitBranch, Clock, CheckCircle2, AlertTriangle, ChevronRight } from "lucide-react";
import Link from "next/link";
import type { Workflow } from "../api";

const STATUS_CONFIG: Record<
  Workflow["status"],
  { label: string; className: string; dot: string }
> = {
  pending:   { label: "Pending",   className: "status-badge status-badge--pending",   dot: "status-dot--pending" },
  running:   { label: "Running",   className: "status-badge status-badge--running",   dot: "status-dot--running" },
  completed: { label: "Completed", className: "status-badge status-badge--completed", dot: "status-dot--completed" },
  failed:    { label: "Failed",    className: "status-badge status-badge--failed",    dot: "status-dot--failed" },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function WorkflowTable({ workflows }: { workflows: Workflow[] }) {
  if (workflows.length === 0) {
    return (
      <div className="table-empty">
        <GitBranch size={28} className="table-empty-icon" />
        <p className="table-empty-text">No workflows yet</p>
        <p className="table-empty-sub">Workflows created by your workers will appear here.</p>
      </div>
    );
  }

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Steps</th>
            <th>Updated</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {workflows.map((wf) => {
            const cfg = STATUS_CONFIG[wf.status];
            return (
              <tr key={wf.id}>
                <td>
                  <div className="table-cell-primary">
                    <div className="table-icon table-icon--violet">
                      <GitBranch size={13} />
                    </div>
                    <div>
                      <p className="table-name font-mono">
                        {(wf.metadata?.name as string) || `Workflow #${wf.id.substring(0, 8)}`}
                      </p>
                      <p className="table-meta">ID: {wf.id}</p>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={cfg.className}>
                    <span className={`status-dot ${cfg.dot}`} />
                    {cfg.label}
                  </span>
                </td>
                <td>
                  <span className="table-steps">{wf.steps_count ?? 0} steps</span>
                </td>
                <td>
                  <span className="table-date">{formatDate(wf.updated_at)}</span>
                </td>
                <td>
                  <Link
                    href={`/dashboard/workflows/${wf.id}`}
                    className="table-action-btn"
                    aria-label={`View workflow ${wf.metadata?.name}`}
                  >
                    <ChevronRight size={15} />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function WorkflowStatusBar({ workflows }: { workflows: Workflow[] }) {
  const counts = { pending: 0, running: 0, completed: 0, failed: 0 };
  for (const wf of workflows) counts[wf.status]++;

  const items = [
    { label: "Pending",   value: counts.pending,   icon: Clock,          cls: "text-amber-400" },
    { label: "Running",   value: counts.running,   icon: GitBranch,      cls: "text-cyan-400" },
    { label: "Completed", value: counts.completed, icon: CheckCircle2,   cls: "text-emerald-400" },
    { label: "Failed",    value: counts.failed,    icon: AlertTriangle,  cls: "text-red-400" },
  ];

  return (
    <div className="status-bar">
      {items.map(({ label, value, icon: Icon, cls }) => (
        <div key={label} className="status-bar-item">
          <Icon size={14} className={cls} />
          <span className="status-bar-value">{value}</span>
          <span className="status-bar-label">{label}</span>
        </div>
      ))}
    </div>
  );
}
