export interface WorkflowSchedule {
  id: string;
  project_id: string;
  workflow_name: string;
  cron_expression: string;
  timezone: string;
  is_active: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduleCreatePayload {
  workflow_name: string;
  cron_expression: string;
  timezone: string;
  is_active: boolean;
}

export interface ScheduleUpdatePayload {
  workflow_name?: string;
  cron_expression?: string;
  timezone?: string;
  is_active?: boolean;
}

export interface ScheduleTriggerResponse {
  schedule: WorkflowSchedule;
  workflow_run_id: string;
}

