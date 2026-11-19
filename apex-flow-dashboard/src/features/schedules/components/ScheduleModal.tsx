"use client";

import { useState } from "react";
import { CalendarClock, Loader2, X } from "lucide-react";
import type {
  ScheduleCreatePayload,
  WorkflowSchedule,
} from "@/features/schedules/types";
import {
  COMMON_TIMEZONES,
  CRON_PRESETS,
  describeCronExpression,
  isValidFiveFieldCron,
} from "@/features/schedules/utils";

interface ScheduleModalProps {
  editingSchedule: WorkflowSchedule | null;
  knownWorkflowNames: string[];
  onClose: () => void;
  onSave: (payload: ScheduleCreatePayload, editingId: string | null) => Promise<void>;
}

export function ScheduleModal({
  editingSchedule,
  knownWorkflowNames,
  onClose,
  onSave,
}: ScheduleModalProps) {
  const [workflowName, setWorkflowName] = useState(editingSchedule?.workflow_name ?? "");
  const [cronExpression, setCronExpression] = useState(
    editingSchedule?.cron_expression ?? "*/5 * * * *"
  );
  const [timezone, setTimezone] = useState(editingSchedule?.timezone ?? "UTC");
  const [isActive, setIsActive] = useState(editingSchedule?.is_active ?? true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timezoneOptions = COMMON_TIMEZONES.includes(timezone)
    ? COMMON_TIMEZONES
    : [timezone, ...COMMON_TIMEZONES];

  const cronPreview = describeCronExpression(cronExpression);
  const cronLooksValid = isValidFiveFieldCron(cronExpression);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedName = workflowName.trim();
    const trimmedCron = cronExpression.trim();

    if (!trimmedName) {
      setError("Workflow name is required.");
      return;
    }
    if (!isValidFiveFieldCron(trimmedCron)) {
      setError("Cron expression must be a valid 5-field expression (min hour dom mon dow).");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await onSave(
        {
          workflow_name: trimmedName,
          cron_expression: trimmedCron,
          timezone,
          is_active: isActive,
        },
        editingSchedule ? editingSchedule.id : null
      );
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save schedule.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-[#161620] border border-white/10 rounded-2xl p-6 shadow-2xl animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-5">
          <h3 className="text-base font-bold text-[#ececee] flex items-center gap-2">
            <CalendarClock size={18} className="text-violet-400" />
            {editingSchedule ? "Edit Schedule" : "Create Scheduled Workflow"}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-400 hover:text-white"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="schedule-workflow-name" className="text-xs font-medium text-zinc-300">
              Workflow Name
            </label>
            <input
              id="schedule-workflow-name"
              list="known-workflow-names"
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              placeholder="e.g. nightly-sync-pipeline"
              className="w-full h-9 px-3 rounded-lg bg-[#0f0f17] border border-white/10 text-xs font-mono text-zinc-100 focus:outline-none focus:border-violet-500"
              required
            />
            <datalist id="known-workflow-names">
              {knownWorkflowNames.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
            <p className="text-[11px] text-zinc-500">
              Must match the name registered via <code className="font-mono">@client.workflow</code>.
            </p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="schedule-cron-expr" className="text-xs font-medium text-zinc-300">
              Cron Expression (5-field)
            </label>
            <input
              id="schedule-cron-expr"
              type="text"
              value={cronExpression}
              onChange={(e) => setCronExpression(e.target.value)}
              placeholder="*/5 * * * *"
              className="w-full h-9 px-3 rounded-lg bg-[#0f0f17] border border-white/10 text-xs font-mono text-violet-200 focus:outline-none focus:border-violet-500"
              required
            />
            <div className="flex flex-wrap gap-1.5 pt-1">
              {CRON_PRESETS.map((preset) => (
                <button
                  key={preset.expression}
                  type="button"
                  onClick={() => setCronExpression(preset.expression)}
                  className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                    cronExpression.trim() === preset.expression
                      ? "bg-violet-600/25 border-violet-500/60 text-violet-200"
                      : "bg-white/5 border-white/10 text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <p
              className={`text-xs pt-1 ${
                cronLooksValid ? "text-emerald-300" : "text-amber-300"
              }`}
            >
              Preview: {cronPreview} ({timezone})
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="schedule-timezone" className="text-xs font-medium text-zinc-300">
                Timezone
              </label>
              <select
                id="schedule-timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full h-9 px-3 rounded-lg bg-[#0f0f17] border border-white/10 text-xs text-zinc-100 focus:outline-none focus:border-violet-500"
              >
                {timezoneOptions.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end pb-1.5">
              <label className="flex items-center gap-2 text-xs text-zinc-200 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded border-white/20 bg-[#0f0f17] text-violet-500 focus:ring-violet-500"
                />
                <span>Schedule active immediately</span>
              </label>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-300">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/10">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg text-xs font-medium text-zinc-300 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="action-btn action-btn--primary text-xs h-9 px-4 disabled:opacity-50"
            >
              {submitting && <Loader2 size={13} className="animate-spin" />}
              <span>{editingSchedule ? "Save Changes" : "Create Schedule"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
