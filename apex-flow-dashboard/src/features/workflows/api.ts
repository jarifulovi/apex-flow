import { fetchWithAuth, fetchWithMeta, type PaginatedResponse } from "@/lib/api";

export async function getWorkflows(
  token: string,
  projectId?: string,
  status?: string,
  limit = 10,
  offset = 0,
  search?: string,
  parentWorkflowId?: string
): Promise<PaginatedResponse<Workflow[]>> {
  const query = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (projectId) {
    query.set("project_id", projectId);
  }
  if (status && status !== "all") {
    query.set("status", status);
  }
  if (search && search.trim()) {
    query.set("search", search.trim());
  }
  if (parentWorkflowId) {
    query.set("parent_workflow_id", parentWorkflowId);
  }
  return fetchWithMeta<Workflow[]>(`/api/v1/workflows?${query.toString()}`, token);
}

export async function getWorkflowStats(
  token: string,
  projectId?: string
): Promise<Record<string, number>> {
  const query = new URLSearchParams();
  if (projectId) {
    query.set("project_id", projectId);
  }
  return fetchWithAuth<Record<string, number>>(`/api/v1/workflows/stats?${query.toString()}`, token);
}

export interface WorkflowStepSummary {
  id: string;
  workflow_run_id: string;
  step_name: string;
  step_order?: number;
  priority?: number;
  status: "queued" | "running" | "success" | "failed" | "cancelled";
  attempt_count: number;
  max_attempts: number;
  locked_until?: string | null;
  available_at?: string;
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
  priority?: number;
  metadata: Record<string, unknown>;
  deduplication_id?: string | null;
  parent_workflow_id?: string | null;
  forked_from_id?: string | null;
  timeout_seconds?: number | null;
  deadline_at?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  steps_count?: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  steps: WorkflowStepSummary[];
  sub_workflows?: Workflow[];
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

export async function forkWorkflowRun(
  token: string,
  workflowId: string,
  options?: {
    from_step_order?: number;
    workflow_name?: string;
    priority?: number;
    metadata_override?: Record<string, unknown>;
  }
): Promise<WorkflowDetail> {
  return fetchWithAuth<WorkflowDetail>(`/api/v1/workflows/${workflowId}/fork`, token, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(options || {}),
  });
}
