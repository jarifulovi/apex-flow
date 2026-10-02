export type WorkerStatus = "active" | "inactive";

export interface Worker {
  id: string;
  project_id: string;
  name: string;
  status: WorkerStatus;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}
