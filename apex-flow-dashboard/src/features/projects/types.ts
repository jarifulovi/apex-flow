import type {
  AlertWindowSeconds,
  MaxAlertsPerWindow,
} from "@/features/settings/types";

export interface ProjectAlertMetadata {
  webhook_url?: string;
  alert_on_failure?: boolean;
  alert_on_timeout?: boolean;
  alert_on_max_retry?: boolean;
  alert_on_worker_disconnect?: boolean;
  window_seconds?: AlertWindowSeconds;
  max_alerts_per_window?: MaxAlertsPerWindow;
}

export interface ProjectMetadata {
  is_default?: boolean;
  alerts?: ProjectAlertMetadata;
  [key: string]: unknown;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  metadata?: ProjectMetadata;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  metadata?: Record<string, unknown>;
}

export interface ProjectUpdatePayload {
  name?: string;
  alerts?: {
    webhook_url: string;
    alert_on_failure: boolean;
    alert_on_timeout: boolean;
    alert_on_max_retry: boolean;
    alert_on_worker_disconnect: boolean;
    window_seconds: AlertWindowSeconds;
    max_alerts_per_window: MaxAlertsPerWindow;
  };
}

export interface WebhookTestResponse {
  ok: boolean;
  status_code: number;
  provider: string;
  latency_ms: number;
  detail: string;
}

export interface ProjectPurgeResponse {
  deleted_runs: number;
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
