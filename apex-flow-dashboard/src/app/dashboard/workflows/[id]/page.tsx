"use client";

import { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import { Header } from "@/components/shared/Header";
import {
  ArrowLeft,
  GitBranch,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Timer,
  ShieldAlert,
  RotateCcw,
  Ban,
  Maximize2,
  FileCode2,
} from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import {
  getWorkflowDetail,
  cancelWorkflowRun,
  restartWorkflowRun,
  formatDurationMs,
  type WorkflowDetail,
  type WorkflowStepSummary,
} from "@/features/workflows/api";
import { Button } from "@/components/ui/button";
import { ErrorInspectorModal } from "@/components/shared/ErrorInspectorModal";
import { PayloadViewerModal } from "@/components/shared/PayloadViewerModal";

const STATUS_CONFIG: Record<
  string,
  { label: string; className: string; dot: string; icon: React.ElementType }
> = {
  pending: { label: "Pending", className: "status-badge status-badge--pending", dot: "status-dot--pending", icon: Clock },
  running: { label: "Running", className: "status-badge status-badge--running", dot: "status-dot--running", icon: Loader2 },
  completed: { label: "Completed", className: "status-badge status-badge--completed", dot: "status-dot--completed", icon: CheckCircle2 },
  success: { label: "Success", className: "status-badge status-badge--completed", dot: "status-dot--completed", icon: CheckCircle2 },
  failed: { label: "Failed", className: "status-badge status-badge--failed", dot: "status-dot--failed", icon: AlertTriangle },
  cancelled: { label: "Cancelled", className: "status-badge status-badge--failed border-amber-500/30 text-amber-300 bg-amber-950/40", dot: "bg-amber-400", icon: Ban },
  queued: { label: "Queued", className: "status-badge status-badge--pending", dot: "status-dot--pending", icon: Clock },
};

function PayloadButton({ label, payload }: { label: string; payload?: Record<string, unknown> }) {
  const [modalOpen, setModalOpen] = useState(false);
  const isEmpty = !payload || Object.keys(payload).length === 0;

  if (isEmpty) return null;

  return (
    <>
      <button
        onClick={() => setModalOpen(true)}
        className="px-2 py-1 rounded bg-[#1b1b28] hover:bg-violet-600/20 border border-white/10 hover:border-violet-500/40 text-[11px] font-mono text-violet-300 hover:text-white flex items-center gap-1.5 transition-colors"
        title={`Inspect ${label}`}
      >
        <FileCode2 size={12} className="text-violet-400" />
        <span>{label}</span>
      </button>

      {modalOpen && (
        <PayloadViewerModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          title={label}
          payload={payload}
        />
      )}
    </>
  );
}

export default function WorkflowDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const workflowId = resolvedParams.id;
  const { accessToken } = useAuth();
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Inspector modal state
  const [selectedErrorStep, setSelectedErrorStep] = useState<{ stepName: string; errorMessage: string } | null>(null);

  const loadDetail = useCallback(async () => {
    if (!accessToken || !workflowId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getWorkflowDetail(accessToken, workflowId);
      setDetail(data);
    } catch (err: any) {
      console.error("Failed to load workflow detail:", err);
      setError(err?.message || "Failed to load workflow details");
    } finally {
      setLoading(false);
    }
  }, [accessToken, workflowId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleCancel = async () => {
    if (!accessToken || !workflowId || actionLoading) return;
    try {
      setActionLoading(true);
      const updated = await cancelWorkflowRun(accessToken, workflowId);
      setDetail(updated);
    } catch (err: any) {
      alert(`Failed to cancel workflow: ${err?.message || err}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestart = async () => {
    if (!accessToken || !workflowId || actionLoading) return;
    try {
      setActionLoading(true);
      const updated = await restartWorkflowRun(accessToken, workflowId);
      setDetail(updated);
    } catch (err: any) {
      alert(`Failed to restart workflow: ${err?.message || err}`);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="dashboard-page">
        <Header title="Workflow Execution Details" />
        <div className="flex items-center justify-center py-20 text-zinc-400">
          <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
          <span>Loading execution timeline...</span>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="dashboard-page">
        <Header title="Workflow Detail" />
        <div className="p-8 text-center bg-[#161620] border border-white/10 rounded-xl text-zinc-300 max-w-xl mx-auto my-12">
          <ShieldAlert size={32} className="text-red-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-zinc-100">Workflow Not Found</h2>
          <p className="text-xs text-zinc-400 mt-2">{error || "Could not retrieve workflow run details."}</p>
          <Link href="/dashboard/workflows" className="inline-block mt-4">
            <Button variant="outline" className="text-xs border-white/10">
              <ArrowLeft size={13} className="mr-1.5" /> Back to Workflows
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const name = detail.workflow_name || (detail.metadata?.name as string) || `Workflow #${detail.id.substring(0, 8)}`;
  const totalDuration = formatDurationMs(detail.started_at || detail.created_at, detail.completed_at);

  const hasRunningOrQueuedSteps = detail.steps.some(
    (s) => s.status === "queued" || s.status === "running"
  );
  const effectiveStatus =
    hasRunningOrQueuedSteps && (detail.status === "pending" || detail.status === "running")
      ? "running"
      : detail.status;

  const statusCfg = STATUS_CONFIG[effectiveStatus] || STATUS_CONFIG.pending;

  const canCancel = effectiveStatus === "pending" || effectiveStatus === "running";
  const canRestart = effectiveStatus === "failed" || effectiveStatus === "cancelled";

  return (
    <div className="dashboard-page">
      <Header
        title={name}
        subtitle={`Workflow Run ID: ${detail.id}`}
        actions={
          <div className="flex items-center gap-2">
            {canCancel && (
              <Button
                onClick={handleCancel}
                disabled={actionLoading}
                variant="outline"
                size="sm"
                className="border-red-500/30 text-red-300 hover:text-white bg-red-950/40 hover:bg-red-900/60 text-xs gap-1.5"
              >
                {actionLoading ? <Loader2 size={13} className="animate-spin" /> : <Ban size={13} />}
                <span>Cancel Run</span>
              </Button>
            )}

            {canRestart && (
              <Button
                onClick={handleRestart}
                disabled={actionLoading}
                variant="outline"
                size="sm"
                className="border-violet-500/30 text-violet-300 hover:text-white bg-violet-950/40 hover:bg-violet-900/60 text-xs gap-1.5"
              >
                {actionLoading ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />}
                <span>Restart Run</span>
              </Button>
            )}

            <Link href="/dashboard/workflows">
              <Button
                variant="outline"
                size="sm"
                className="border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] text-xs gap-1.5"
              >
                <ArrowLeft size={13} />
                <span>Back</span>
              </Button>
            </Link>
          </div>
        }
      />

      <div className="page-content space-y-6">
        {/* Workflow Overview Banner */}
        <div className="bg-[#161620] border border-white/10 rounded-xl p-6 shadow-xl grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
              Execution Status
            </span>
            <span className={statusCfg.className}>
              <span className={`status-dot ${statusCfg.dot}`} />
              {statusCfg.label}
            </span>
          </div>

          <div>
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
              Total Duration
            </span>
            <span className="text-sm font-semibold text-zinc-100 font-mono flex items-center gap-1.5">
              <Timer size={14} className="text-violet-400" />
              {totalDuration}
            </span>
          </div>

          <div>
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
              Executed Steps
            </span>
            <span className="text-sm font-semibold text-zinc-100 font-mono">
              {detail.steps.length} Steps
            </span>
          </div>

          <div>
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block mb-1">
              Started At
            </span>
            <span className="text-xs text-zinc-300 font-mono">
              {detail.started_at || detail.created_at
                ? new Date(detail.started_at || detail.created_at).toLocaleString()
                : "—"}
            </span>
          </div>
        </div>

        {/* Step Execution Timeline */}
        <section className="dashboard-section" aria-labelledby="steps-timeline-heading">
          <div className="dashboard-section-header">
            <GitBranch size={15} className="section-icon text-violet-400" />
            <h2 id="steps-timeline-heading" className="dashboard-section-title">
              Execution Step Timeline
            </h2>
          </div>

          {detail.steps.length === 0 ? (
            <div className="table-empty">
              <Clock size={28} className="table-empty-icon text-zinc-500" />
              <p className="table-empty-text">No steps recorded yet</p>
              <p className="table-empty-sub">Steps executed in this workflow will appear here in order.</p>
            </div>
          ) : (
            <div className="relative pl-6 space-y-3 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-white/10">
              {detail.steps.map((step: WorkflowStepSummary, index: number) => {
                const sCfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.queued;
                const Icon = sCfg.icon;
                const stepDuration = formatDurationMs(step.started_at || step.created_at, step.completed_at);

                return (
                  <div key={step.id} className="relative group">
                    {/* Timeline Node Dot */}
                    <div
                      className={`absolute -left-[1.85rem] top-2.5 h-3.5 w-3.5 rounded-full border-2 border-[#111118] flex items-center justify-center ${
                        step.status === "success"
                          ? "bg-emerald-400"
                          : step.status === "failed"
                          ? "bg-red-500 animate-pulse"
                          : step.status === "cancelled"
                          ? "bg-amber-400"
                          : step.status === "running"
                          ? "bg-cyan-400 animate-ping"
                          : "bg-amber-400"
                      }`}
                    />

                    <div className="bg-[#161620] border border-white/10 rounded-xl p-3 sm:p-3.5 transition-all hover:border-violet-500/40">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2.5">
                          <span className="text-[11px] font-mono font-bold text-violet-400 bg-violet-950/60 border border-violet-500/30 px-2 py-0.5 rounded">
                            Step #{step.step_order || index + 1}
                          </span>
                          <h3 className="text-xs sm:text-sm font-semibold text-zinc-100 font-mono">
                            {step.step_name}
                          </h3>
                        </div>

                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-xs text-zinc-400 font-mono flex items-center gap-1">
                            <Timer size={12} className="text-zinc-500" />
                            {stepDuration}
                          </span>
                          <span className="text-xs text-zinc-400 font-mono">
                            Attempts: {step.attempt_count}/{step.max_attempts}
                          </span>
                          <span className={sCfg.className}>
                            <Icon size={12} className={step.status === "running" ? "animate-spin mr-1" : "mr-1"} />
                            {sCfg.label}
                          </span>

                          <div className="flex items-center gap-1.5 ml-1">
                            <PayloadButton label="Input JSON" payload={step.input_payload} />
                            <PayloadButton label="Output JSON" payload={step.output_payload} />
                          </div>
                        </div>
                      </div>

                      {step.error_message && (
                        <div className="mt-2.5 p-2.5 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300 font-mono flex items-start justify-between gap-3">
                          <div>
                            <span className="font-bold block text-red-400 mb-0.5 flex items-center gap-1.5">
                              <AlertTriangle size={13} />
                              Execution Failure:
                            </span>
                            <span className="line-clamp-2">{step.error_message}</span>
                          </div>
                          <Button
                            onClick={() =>
                              setSelectedErrorStep({
                                stepName: step.step_name,
                                errorMessage: step.error_message!,
                              })
                            }
                            variant="outline"
                            size="sm"
                            className="h-6 text-[11px] border-red-500/40 text-red-300 hover:text-white bg-red-900/40 shrink-0 gap-1 px-2"
                          >
                            <Maximize2 size={11} />
                            <span>Inspect Error</span>
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {/* Error Inspector Modal */}
      <ErrorInspectorModal
        isOpen={!!selectedErrorStep}
        onClose={() => setSelectedErrorStep(null)}
        stepName={selectedErrorStep?.stepName || ""}
        errorMessage={selectedErrorStep?.errorMessage || ""}
      />
    </div>
  );
}
