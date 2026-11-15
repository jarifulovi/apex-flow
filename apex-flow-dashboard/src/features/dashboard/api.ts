import { getWorkflows } from "@/features/workflows/api";
import { getProjectKeys } from "@/features/project-keys/api";
import { getWorkers } from "@/features/workers/api";
import { getProjectMetrics, getProjectOverview } from "@/features/projects/api";

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
  if (projectId) {
    try {
      const overview = await getProjectOverview(token, projectId);
      const s = overview.stats || {};
      return {
        stats: {
          totalWorkflows: s.total_runs ?? 0,
          activeSteps: s.running_runs ?? 0,
          completedSteps: s.completed_runs ?? 0,
          failedSteps: s.failed_runs ?? 0,
          activeKeysCount: s.active_workers_count ?? 0,
          activeWorkersCount: s.active_workers_count ?? 0,
          successRatePercent: s.success_rate_percent ?? 0.0,
          avgDurationSeconds: s.avg_duration_seconds ?? 0.0,
        },
        activities: (overview.activities || []).map((act: any) => ({
          id: act.id,
          workflowId: act.workflow_id,
          stepName: act.step_name,
          status: act.status,
          timestamp: act.timestamp,
          errorMessage: act.error_message,
        })),
        keys: [],
        workers: [],
        hasKeys: Boolean(overview.has_keys),
        hasWorkflows: Boolean(overview.has_workflows),
      };
    } catch (err) {
      console.warn("Consolidated overview fetch failed, falling back...", err);
    }
  }

  const [workflowsRes, keys, workers, metrics] = await Promise.all([
    getWorkflows(token, projectId, "all", 10, 0).catch(() => ({ data: [], totalCount: 0 })),
    getProjectKeys(token, projectId).catch(() => []),
    getWorkers(token, projectId).catch(() => []),
    projectId ? getProjectMetrics(token, projectId).catch(() => null) : Promise.resolve(null),
  ]);

  const workflows = workflowsRes.data;

  const totalWorkflows = metrics?.total_runs ?? workflowsRes.totalCount;
  const activeSteps = workflows.filter((w) => w.status === "running" || w.status === "pending").length;
  const completedSteps = workflows.filter((w) => w.status === "completed").length;
  const failedSteps = workflows.filter((w) => w.status === "failed").length;
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

  const activities: ActivityItem[] = workflows
    .slice(0, 6)
    .map((w) => ({
      id: w.id,
      workflowId: w.id,
      stepName: w.workflow_name,
      status: (w.status === "completed" ? "success" : w.status) as ActivityItem["status"],
      timestamp: w.updated_at || w.created_at,
      errorMessage: w.error_message,
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
