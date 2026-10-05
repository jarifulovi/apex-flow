import { getWorkflows } from "@/features/workflows/api";
import { getSteps } from "@/features/steps/api";
import { getProjectKeys } from "@/features/project-keys/api";
import { getWorkers } from "@/features/workers/api";

export interface DashboardStats {
  totalWorkflows: number;
  activeSteps: number;
  completedSteps: number;
  failedSteps: number;
  activeKeysCount: number;
  activeWorkersCount: number;
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
  const [workflows, steps, keys, workers] = await Promise.all([
    getWorkflows(token, projectId, 100, 0).catch(() => []),
    getSteps(token, projectId, "all", 100, 0).catch(() => []),
    getProjectKeys(token, projectId).catch(() => []),
    getWorkers(token, projectId).catch(() => []),
  ]);

  const totalWorkflows = workflows.length;
  const activeSteps = steps.filter((s) => s.status === "queued" || s.status === "running").length;
  const completedSteps = steps.filter((s) => s.status === "success").length;
  const failedSteps = steps.filter((s) => s.status === "failed").length;
  const activeKeysCount = keys.filter((k) => k.status === "active").length;

  const now = Date.now();
  const activeWorkersCount = workers.filter(
    (w) => w.status === "active" && w.last_seen_at && (now - new Date(w.last_seen_at).getTime()) < 60000
  ).length;

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
    },
    activities,
    keys,
    workers,
    hasKeys: keys.length > 0,
    hasWorkflows: workflows.length > 0,
  };
}
