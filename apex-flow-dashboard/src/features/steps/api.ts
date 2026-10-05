import { fetchWithAuth, fetchWithMeta, type PaginatedResponse } from "@/lib/api";

export interface WorkflowStep {
  id: string;
  workflow_run_id: string;
  step_name: string;
  step_order?: number;
  status: "queued" | "running" | "success" | "failed" | "cancelled";
  attempt_count: number;
  max_attempts: number;
  locked_until?: string | null;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  error_message: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export async function getSteps(
  token: string,
  projectId?: string,
  statusFilter?: string,
  limit = 10,
  offset = 0,
  search?: string
): Promise<PaginatedResponse<WorkflowStep[]>> {
  const query = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (projectId) {
    query.set("project_id", projectId);
  }
  if (statusFilter && statusFilter !== "all") {
    query.set("status", statusFilter);
  }
  if (search && search.trim()) {
    query.set("search", search.trim());
  }
  return fetchWithMeta<WorkflowStep[]>(`/api/v1/steps?${query.toString()}`, token);
}

export async function getStepStats(
  token: string,
  projectId?: string
): Promise<Record<string, number>> {
  const query = new URLSearchParams();
  if (projectId) {
    query.set("project_id", projectId);
  }
  return fetchWithAuth<Record<string, number>>(`/api/v1/steps/stats?${query.toString()}`, token);
}
