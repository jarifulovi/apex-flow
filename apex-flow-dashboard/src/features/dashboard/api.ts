import { getWorkflows } from "@/features/workflows/api";
import { getSteps } from "@/features/steps/api";
import { getProjectKeys } from "@/features/project-keys/api";
import { getWorkers } from "@/features/workers/api";
import { getProjectMetrics } from "@/features/projects/api";

export interface DashboardStats {
  totalWorkflows: number;
  activeSteps: number;
  completedSteps: number;
  failedSteps: number;
  activeKeysCount: number;
  activeWorkersCount: number;
  successRatePercent: number;
  avgDurationSeconds: number;
}

export interface ActivityItem {
  id: string;
  workflowId: string;
  stepName: string;
  status: "queued" | "running" | "success" | "failed" | "cancelled";
  timestamp: string;
  errorMessage?: string | null;
}

export async function fetchDashboardOverview(token: string, projectId?: string) {
  const [workflowsRes, stepsRes, keys, workers, metrics] = await Promise.all([
    getWorkflows(token, projectId, "all", 100, 0).catch(() => ({ data: [], totalCount: 0 })),
    getSteps(token, projectId, "all", 100, 0).catch(() => ({ data: [], totalCount: 0 })),
    getProjectKeys(token, projectId).catch(() => []),
    getWorkers(token, projectId).catch(() => []),
    projectId ? getProjectMetrics(token, projectId).catch(() => null) : Promise.resolve(null),
  ]);

  const workflows = workflowsRes.data;
  const steps = stepsRes.data;

  const totalWorkflows = metrics?.total_runs ?? workflowsRes.totalCount;
  const activeSteps = steps.filter((s) => s.status === "queued" || s.status === "running").length;
  const completedSteps = steps.filter((s) => s.status === "success").length;
  const failedSteps = steps.filter((s) => s.status === "failed").length;
  const activeKeysCount = keys.filter((k) => k.status === "active").length;

  const now = Date.now();
  const activeWorkersCount = metrics?.active_workers_count ?? workers.filter(
    (w) => w.status === "active" && w.last_seen_at && (now - new Date(w.last_seen_at).getTime()) < 60000
  ).length;

  const completedWfs = workflows.filter((w) => w.status === "completed").length;
  const successRatePercent = metrics?.success_rate_percent ?? (
    workflows.length > 0 ? Math.round((completedWfs / workflows.length) * 1000) / 10 : 0.0
  );
  const avgDurationSeconds = metrics?.avg_duration_seconds ?? 0.0;

  const activities: ActivityItem[] = steps
    .slice(0, 6)
    .map((s) => ({
      id: s.id,
      workflowId: s.workflow_run_id || (s as any).workflow_id,
      stepName: s.step_name,
      status: s.status,
      timestamp: s.updated_at || s.created_at,
      errorMessage: s.error_message,
    }));

  return {
    stats: {
      totalWorkflows,
      activeSteps,
      completedSteps,
      failedSteps,
      activeKeysCount,
      activeWorkersCount,
      successRatePercent,
      avgDurationSeconds,
    },
    activities,
    keys,
    workers,
    hasKeys: keys.length > 0,
    hasWorkflows: workflows.length > 0,
  };
}
