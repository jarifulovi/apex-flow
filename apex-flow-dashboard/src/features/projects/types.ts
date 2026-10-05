export interface Project {
  id: string;
  owner_id: string;
  name: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  metadata?: Record<string, unknown>;
}

export interface ProjectMetrics {
  project_id: string;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  running_runs: number;
  cancelled_runs: number;
  success_rate_percent: number;
  active_workers_count: number;
  avg_duration_seconds: number;
}
