import { fetchWithAuth } from "@/lib/api";

export interface WorkflowStepSummary {
  id: string;
  workflow_run_id: string;
  step_name: string;
  status: "queued" | "running" | "success" | "failed" | "cancelled";
  attempt_count: number;
  max_attempts: number;
  locked_until?: string | null;
  input_payload?: Record<string, unknown>;
  output_payload?: Record<string, unknown>;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Workflow {
  id: string;
  project_id: string;
  workflow_name: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  metadata: Record<string, unknown>;
  started_at?: string | null;
  completed_at?: string | null;
  steps_count?: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  steps: WorkflowStepSummary[];
}

export function formatDurationMs(startedAt?: string | null, completedAt?: string | null): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const diffMs = Math.max(0, end - start);

  if (diffMs < 1000) return `${diffMs}ms`;
  if (diffMs < 60000) return `${(diffMs / 1000).toFixed(1)}s`;
  const mins = Math.floor(diffMs / 60000);
  const secs = Math.floor((diffMs % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

export async function getWorkflows(
  token: string,
  projectId?: string,
  limit = 50,
  offset = 0
): Promise<Workflow[]> {
  const query = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (projectId) {
    query.set("project_id", projectId);
  }
  return fetchWithAuth<Workflow[]>(`/api/v1/workflows?${query.toString()}`, token);
}

export async function getWorkflowDetail(token: string, workflowId: string): Promise<WorkflowDetail> {
  return fetchWithAuth<WorkflowDetail>(`/api/v1/workflows/${workflowId}`, token);
}

export async function cancelWorkflowRun(token: string, workflowId: string): Promise<WorkflowDetail> {
  return fetchWithAuth<WorkflowDetail>(`/api/v1/workflows/${workflowId}/cancel`, token, {
    method: "POST",
  });
}

export async function restartWorkflowRun(token: string, workflowId: string): Promise<WorkflowDetail> {
  return fetchWithAuth<WorkflowDetail>(`/api/v1/workflows/${workflowId}/restart`, token, {
    method: "POST",
  });
}
