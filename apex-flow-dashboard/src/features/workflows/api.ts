import { fetchWithAuth } from "@/lib/api";

export interface WorkflowStepSummary {
  id: string;
  workflow_id: string;
  step_name: string;
  status: "queued" | "running" | "success" | "failed";
  attempt_count: number;
  input_payload?: Record<string, unknown>;
  output_payload?: Record<string, unknown>;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Workflow {
  id: string;
  user_id: string;
  status: "pending" | "running" | "completed" | "failed";
  metadata: Record<string, unknown>;
  steps_count?: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  steps: WorkflowStepSummary[];
}

export async function getWorkflows(token: string, limit = 50, offset = 0): Promise<Workflow[]> {
  return fetchWithAuth<Workflow[]>(`/api/v1/workflows?limit=${limit}&offset=${offset}`, token);
}

export async function getWorkflowDetail(token: string, workflowId: string): Promise<WorkflowDetail> {
  return fetchWithAuth<WorkflowDetail>(`/api/v1/workflows/${workflowId}`, token);
}
