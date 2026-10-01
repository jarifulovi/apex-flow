import { fetchWithAuth } from "@/lib/api";

export interface WorkflowStep {
  id: string;
  workflow_id: string;
  step_name: string;
  status: "queued" | "running" | "success" | "failed";
  attempt_count: number;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export async function getSteps(
  token: string,
  statusFilter?: string,
  limit = 50,
  offset = 0
): Promise<WorkflowStep[]> {
  const query = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (statusFilter && statusFilter !== "all") {
    query.set("status", statusFilter);
  }
  return fetchWithAuth<WorkflowStep[]>(`/api/v1/steps?${query.toString()}`, token);
}
