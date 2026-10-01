import { getWorkflows } from "@/features/workflows/api";
import { getSteps } from "@/features/steps/api";
import { getProjectKeys } from "@/features/project-keys/api";

export interface DashboardStats {
  totalWorkflows: number;
  activeSteps: number;
  completedSteps: number;
  failedSteps: number;
  activeKeysCount: number;
}

export interface ActivityItem {
  id: string;
  workflowId: string;
  stepName: string;
  status: "queued" | "running" | "success" | "failed";
  timestamp: string;
  errorMessage?: string | null;
}

export async function fetchDashboardOverview(token: string) {
  const [workflows, steps, keys] = await Promise.all([
    getWorkflows(token, 100, 0).catch(() => []),
    getSteps(token, "all", 100, 0).catch(() => []),
    getProjectKeys(token).catch(() => []),
  ]);

  const totalWorkflows = workflows.length;
  const activeSteps = steps.filter((s) => s.status === "queued" || s.status === "running").length;
  const completedSteps = steps.filter((s) => s.status === "success").length;
  const failedSteps = steps.filter((s) => s.status === "failed").length;
  const activeKeysCount = keys.filter((k) => k.status === "active").length;

  const activities: ActivityItem[] = steps
    .slice(0, 10)
    .map((s) => ({
      id: s.id,
      workflowId: s.workflow_id,
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
    },
    activities,
    keys,
    hasKeys: keys.length > 0,
    hasWorkflows: workflows.length > 0,
  };
}
