import React, { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Clock,
  Timer,
  Lock,
  XCircle,
  FileCode2,
  Maximize2,
} from "lucide-react";
import type { WorkflowStep } from "@/features/steps/api";
import { formatDurationMs } from "@/features/workflows/api";
import { PayloadViewerModal } from "@/components/shared/PayloadViewerModal";
import { ErrorInspectorModal } from "@/components/shared/ErrorInspectorModal";

const STATUS_CONFIG: Record<
  WorkflowStep["status"],
  { label: string; className: string; dot: string; icon: React.ElementType }
> = {
  queued: { label: "Queued", className: "status-badge status-badge--pending", dot: "status-dot--pending", icon: Clock },
  running: { label: "Running", className: "status-badge status-badge--running", dot: "status-dot--running", icon: Loader2 },
  success: { label: "Success", className: "status-badge status-badge--completed", dot: "status-dot--completed", icon: CheckCircle2 },
  failed: { label: "Failed", className: "status-badge status-badge--failed", dot: "status-dot--failed", icon: AlertTriangle },
  cancelled: { label: "Cancelled", className: "status-badge status-badge--cancelled", dot: "status-dot--failed", icon: XCircle },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function PayloadCell({
  payload,
  label,
  stepName,
}: {
  payload?: Record<string, unknown>;
  label: string;
  stepName: string;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const isEmpty = !payload || Object.keys(payload).length === 0;
  const isOffloaded = Boolean(
    payload &&
      typeof payload === "object" &&
      (payload as Record<string, unknown>).$apexflow_ref === true
  );

  return (
    <>
      <button
        className={`px-2 py-1 rounded border text-[11px] font-mono flex items-center gap-1.5 transition-colors ${
          isOffloaded
            ? "bg-amber-500/10 hover:bg-amber-500/20 border-amber-500/30 text-amber-300 hover:text-amber-100 font-semibold"
            : isEmpty
            ? "bg-[#161622]/60 hover:bg-[#161622] border-white/5 text-zinc-500 hover:text-zinc-300"
            : "bg-[#161622] hover:bg-violet-600/20 border-white/10 text-violet-300 hover:text-white"
        }`}
        onClick={() => setModalOpen(true)}
        title={`Inspect ${label} Payload`}
      >
        <FileCode2 size={12} className={isOffloaded ? "text-amber-400" : isEmpty ? "text-zinc-500" : "text-violet-400"} />
        <span>{isOffloaded ? `📦 ${label}` : label}</span>
      </button>

      {modalOpen && (
        <PayloadViewerModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          title={`${label} Payload • ${stepName}`}
          payload={payload || {}}
        />
      )}
    </>
  );
}

export function StepsTable({ steps }: { steps: WorkflowStep[] }) {
  const [selectedErrorStep, setSelectedErrorStep] = useState<{
    stepName: string;
    errorMessage: string;
  } | null>(null);

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
    <>
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Step Name</th>
              <th>Workflow Run</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Attempts</th>
              <th>Input</th>
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
                        <div className="flex items-center gap-1.5">
                          <p className="table-name font-mono">{step.step_name}</p>
                          {step.step_order !== undefined && step.step_order !== null && (
                            <span className="px-1.5 py-0.5 rounded bg-zinc-800/80 border border-white/10 text-[10px] text-violet-300 font-mono" title={`Step Order: ${step.step_order}`}>
                              #{step.step_order}
                            </span>
                          )}
                        </div>
                        {isLocked && (
                          <span className="text-[10px] text-amber-400 font-mono flex items-center gap-1 mt-0.5">
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
                    <PayloadCell payload={step.input_payload} label="Input" stepName={step.step_name} />
                  </td>
                  <td>
                    <PayloadCell payload={step.output_payload} label="Output" stepName={step.step_name} />
                  </td>
                  <td>
                    {step.error_message ? (
                      <button
                        onClick={() =>
                          setSelectedErrorStep({
                            stepName: step.step_name,
                            errorMessage: step.error_message!,
                          })
                        }
                        className="px-2 py-1 rounded bg-red-950/40 hover:bg-red-900/60 border border-red-500/30 text-[11px] font-mono text-red-300 hover:text-white flex items-center gap-1 transition-colors"
                        title="Inspect error traceback"
                      >
                        <Maximize2 size={11} />
                        <span>Inspect Error</span>
                      </button>
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

      <ErrorInspectorModal
        isOpen={!!selectedErrorStep}
        onClose={() => setSelectedErrorStep(null)}
        stepName={selectedErrorStep?.stepName || ""}
        errorMessage={selectedErrorStep?.errorMessage || ""}
      />
    </>
  );
}
