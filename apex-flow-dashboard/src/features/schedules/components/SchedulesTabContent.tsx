"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Loader2,
  Plus,
  X,
} from "lucide-react";
import {
  createSchedule,
  deleteSchedule,
  getSchedules,
  pauseSchedule,
  resumeSchedule,
  triggerScheduleNow,
  updateSchedule,
} from "@/features/schedules/api";
import { ScheduleModal } from "@/features/schedules/components/ScheduleModal";
import { ScheduleTable } from "@/features/schedules/components/ScheduleTable";
import type {
  ScheduleCreatePayload,
  WorkflowSchedule,
} from "@/features/schedules/types";

interface SchedulesTabContentProps {
  accessToken: string | null;
  projectId?: string;
  searchQuery: string;
  knownWorkflowNames: string[];
  refreshSignal: number;
  onCountChange?: (count: number) => void;
  onLoadingChange?: (loading: boolean) => void;
}

interface TriggerNotice {
  workflowName: string;
  workflowRunId: string;
}

export function SchedulesTabContent({
  accessToken,
  projectId,
  searchQuery,
  knownWorkflowNames,
  refreshSignal,
  onCountChange,
  onLoadingChange,
}: SchedulesTabContentProps) {
  const [schedules, setSchedules] = useState<WorkflowSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggerNotice, setTriggerNotice] = useState<TriggerNotice | null>(null);
  const [busyIds, setBusyIds] = useState<Record<string, string | undefined>>({});
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<WorkflowSchedule | null>(null);

  const reloadSchedules = useCallback(async () => {
    if (!accessToken || !projectId) return;
    const data = await getSchedules(accessToken, projectId);
    setSchedules(data);
    onCountChange?.(data.length);
  }, [accessToken, projectId, onCountChange]);

  useEffect(() => {
    let active = true;

    async function fetchSchedules() {
      if (!accessToken || !projectId) {
        if (!active) return;
        setSchedules([]);
        setLoading(false);
        onCountChange?.(0);
        onLoadingChange?.(false);
        return;
      }

      onLoadingChange?.(true);
      try {
        const data = await getSchedules(accessToken, projectId);
        if (!active) return;
        setSchedules(data);
        setError(null);
        onCountChange?.(data.length);
      } catch (err: unknown) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load workflow schedules.");
      } finally {
        if (active) {
          setLoading(false);
          onLoadingChange?.(false);
        }
      }
    }

    void fetchSchedules();
    return () => {
      active = false;
    };
  }, [accessToken, projectId, refreshSignal, onCountChange, onLoadingChange]);

  const filteredSchedules = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return schedules;
    return schedules.filter(
      (s) =>
        s.workflow_name.toLowerCase().includes(q) ||
        s.cron_expression.toLowerCase().includes(q) ||
        s.timezone.toLowerCase().includes(q)
    );
  }, [schedules, searchQuery]);

  const setRowBusy = (id: string, action?: string) => {
    setBusyIds((prev) => ({ ...prev, [id]: action }));
  };

  const handleSaveSchedule = async (
    payload: ScheduleCreatePayload,
    editingId: string | null
  ) => {
    if (!accessToken || !projectId) {
      throw new Error("Select a project before saving a schedule.");
    }
    if (editingId) {
      await updateSchedule(accessToken, projectId, editingId, payload);
    } else {
      await createSchedule(accessToken, projectId, payload);
    }
    await reloadSchedules();
  };

  const handleToggleActive = async (schedule: WorkflowSchedule) => {
    if (!accessToken || !projectId) return;
    setRowBusy(schedule.id, "toggle");
    setError(null);
    try {
      const updated = schedule.is_active
        ? await pauseSchedule(accessToken, projectId, schedule.id)
        : await resumeSchedule(accessToken, projectId, schedule.id);
      setSchedules((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update schedule status.");
    } finally {
      setRowBusy(schedule.id, undefined);
    }
  };

  const handleRunNow = async (schedule: WorkflowSchedule) => {
    if (!accessToken || !projectId) return;
    setRowBusy(schedule.id, "run");
    setError(null);
    try {
      const res = await triggerScheduleNow(accessToken, projectId, schedule.id);
      setSchedules((prev) =>
        prev.map((item) => (item.id === res.schedule.id ? res.schedule : item))
      );
      setTriggerNotice({
        workflowName: res.schedule.workflow_name,
        workflowRunId: res.workflow_run_id,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to trigger scheduled workflow.");
    } finally {
      setRowBusy(schedule.id, undefined);
    }
  };

  const handleDelete = async (scheduleId: string) => {
    if (!accessToken || !projectId) return;
    setRowBusy(scheduleId, "delete");
    setError(null);
    try {
      await deleteSchedule(accessToken, projectId, scheduleId);
      const remaining = schedules.filter((item) => item.id !== scheduleId);
      setSchedules(remaining);
      onCountChange?.(remaining.length);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete schedule.");
    } finally {
      setRowBusy(scheduleId, undefined);
    }
  };

  const activeCount = schedules.filter((s) => s.is_active).length;

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center justify-between gap-3 text-xs text-red-200">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} className="text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-red-300 hover:text-white"
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {triggerNotice && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between gap-3 text-xs text-emerald-200">
          <div className="flex items-center gap-2 flex-wrap">
            <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
            <span>
              Triggered <strong className="font-mono">{triggerNotice.workflowName}</strong>{" "}
              immediately.
            </span>
            <Link
              href={`/dashboard/workflows/${encodeURIComponent(triggerNotice.workflowName)}/${triggerNotice.workflowRunId}`}
              className="underline font-semibold text-emerald-300 hover:text-white"
            >
              Inspect Run ({triggerNotice.workflowRunId.slice(0, 8)})
            </Link>
          </div>
          <button
            type="button"
            onClick={() => setTriggerNotice(null)}
            className="text-emerald-300 hover:text-white"
            aria-label="Dismiss notice"
          >
            <X size={14} />
          </button>
        </div>
      )}

      <section className="dashboard-section" aria-labelledby="schedules-table-heading">
        <div className="dashboard-section-header flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarClock size={15} className="section-icon text-violet-400" />
            <h2 id="schedules-table-heading" className="dashboard-section-title">
              Scheduled Workflows
              <span className="section-count">
                {activeCount} active / {schedules.length} total
              </span>
            </h2>
          </div>

          <button
            type="button"
            onClick={() => {
              setEditingSchedule(null);
              setModalOpen(true);
            }}
            disabled={!projectId}
            className="action-btn action-btn--primary text-xs h-8 px-3 disabled:opacity-50"
          >
            <Plus size={14} />
            <span>New Schedule</span>
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12 text-zinc-400">
            <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
            <span>Loading workflow schedules...</span>
          </div>
        ) : (
          <ScheduleTable
            schedules={filteredSchedules}
            busyIds={busyIds}
            onToggleActive={handleToggleActive}
            onRunNow={handleRunNow}
            onEdit={(schedule) => {
              setEditingSchedule(schedule);
              setModalOpen(true);
            }}
            onDelete={handleDelete}
          />
        )}
      </section>

      {modalOpen && (
        <ScheduleModal
          key={editingSchedule ? editingSchedule.id : "new"}
          editingSchedule={editingSchedule}
          knownWorkflowNames={knownWorkflowNames}
          onClose={() => {
            setModalOpen(false);
            setEditingSchedule(null);
          }}
          onSave={handleSaveSchedule}
        />
      )}
    </div>
  );
}
