"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CalendarClock,
  Clock,
  Loader2,
  Pause,
  Pencil,
  Play,
  Trash2,
  Zap,
} from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { WorkflowSchedule } from "@/features/schedules/types";
import {
  describeCronExpression,
  formatCountdown,
  formatScheduleTimestamp,
} from "@/features/schedules/utils";

interface ScheduleTableProps {
  schedules: WorkflowSchedule[];
  busyIds: Record<string, string | undefined>;
  onToggleActive: (schedule: WorkflowSchedule) => void;
  onRunNow: (schedule: WorkflowSchedule) => void;
  onEdit: (schedule: WorkflowSchedule) => void;
  onDelete: (scheduleId: string) => void;
}

export function ScheduleTable({
  schedules,
  busyIds,
  onToggleActive,
  onRunNow,
  onEdit,
  onDelete,
}: ScheduleTableProps) {
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNowMs(Date.now()), 15000);
    return () => clearInterval(timer);
  }, []);

  if (schedules.length === 0) {
    return (
      <div className="table-empty">
        <CalendarClock size={28} className="table-empty-icon" />
        <p className="table-empty-text">No scheduled workflows found</p>
        <p className="table-empty-sub">
          Create a schedule here or declare{" "}
          <code className="font-mono text-violet-300">@client.workflow(..., cron=&quot;*/5 * * * *&quot;)</code>{" "}
          in your Python worker.
        </p>
      </div>
    );
  }

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Workflow</th>
            <th>Cron Schedule</th>
            <th>Status</th>
            <th>Next Run</th>
            <th>Last Run</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {schedules.map((schedule) => {
            const busyAction = busyIds[schedule.id];
            const isBusy = Boolean(busyAction);
            const workflowHref = `/dashboard/workflows/${encodeURIComponent(schedule.workflow_name)}`;
            const humanText = describeCronExpression(schedule.cron_expression);
            const countdown = schedule.is_active
              ? formatCountdown(schedule.next_run_at, nowMs)
              : "Paused";

            return (
              <tr key={schedule.id}>
                <td>
                  <div className="table-cell-primary">
                    <div
                      className={`table-icon ${
                        schedule.is_active ? "table-icon--violet" : "bg-zinc-800/80 text-zinc-400"
                      }`}
                    >
                      <CalendarClock size={14} />
                    </div>
                    <div>
                      <Link
                        href={workflowHref}
                        className="table-name font-mono hover:text-violet-300 transition-colors"
                      >
                        {schedule.workflow_name}
                      </Link>
                      <p className="table-meta">View runs &amp; history</p>
                    </div>
                  </div>
                </td>

                <td>
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <code className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-xs font-mono text-violet-300">
                        {schedule.cron_expression}
                      </code>
                      <span className="text-[10px] font-mono text-zinc-400 px-1.5 py-0.5 rounded bg-white/5">
                        {schedule.timezone}
                      </span>
                    </div>
                    <span className="text-xs text-zinc-400">{humanText}</span>
                  </div>
                </td>

                <td>
                  <span
                    className={
                      schedule.is_active
                        ? "status-badge status-badge--completed"
                        : "status-badge status-badge--pending"
                    }
                  >
                    <span
                      className={`status-dot ${
                        schedule.is_active ? "status-dot--completed" : "status-dot--pending"
                      }`}
                    />
                    {schedule.is_active ? "Active" : "Paused"}
                  </span>
                </td>

                <td>
                  <div className="flex flex-col gap-0.5">
                    <span
                      className={`flex items-center gap-1.5 text-xs font-mono ${
                        schedule.is_active ? "text-cyan-300" : "text-zinc-500"
                      }`}
                    >
                      <Clock size={12} className="opacity-70" />
                      {countdown}
                    </span>
                    {schedule.is_active && schedule.next_run_at && (
                      <span className="text-[11px] text-zinc-500">
                        {formatScheduleTimestamp(schedule.next_run_at)}
                      </span>
                    )}
                  </div>
                </td>

                <td>
                  <span className="table-date">
                    {formatScheduleTimestamp(schedule.last_run_at)}
                  </span>
                </td>

                <td>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => onRunNow(schedule)}
                      className="px-2.5 py-1.5 rounded-lg bg-violet-600/15 hover:bg-violet-600 border border-violet-500/30 hover:border-violet-500 text-xs font-semibold text-violet-300 hover:text-white transition-all flex items-center gap-1.5 disabled:opacity-50 whitespace-nowrap"
                      title="Trigger an immediate workflow run"
                    >
                      {busyAction === "run" ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Zap size={12} />
                      )}
                      <span>Run Now</span>
                    </button>

                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => onToggleActive(schedule)}
                      className="icon-btn disabled:opacity-50"
                      title={schedule.is_active ? "Pause schedule" : "Resume schedule"}
                      aria-label={schedule.is_active ? "Pause schedule" : "Resume schedule"}
                    >
                      {busyAction === "toggle" ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : schedule.is_active ? (
                        <Pause size={13} className="text-amber-300" />
                      ) : (
                        <Play size={13} className="text-emerald-400" />
                      )}
                    </button>

                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => onEdit(schedule)}
                      className="icon-btn disabled:opacity-50"
                      title="Edit schedule"
                      aria-label="Edit schedule"
                    >
                      <Pencil size={13} />
                    </button>

                    <AlertDialog>
                      <AlertDialogTrigger
                        className="icon-btn hover:text-red-400 disabled:opacity-50"
                        title="Delete schedule"
                        render={<button type="button" disabled={isBusy} />}
                      >
                        <Trash2 size={13} />
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete schedule?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently delete the recurring schedule for{" "}
                            <strong className="text-white">{schedule.workflow_name}</strong>.
                            Past execution runs will remain intact.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => onDelete(schedule.id)}
                            className="bg-red-600 hover:bg-red-700 text-white"
                          >
                            Delete Schedule
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

