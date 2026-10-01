// Dummy data for dashboard overview — aligned to backend WorkflowResponse & WorkflowStepResponse shapes

export interface DashboardStats {
  totalWorkflows: number;
  pendingSteps: number;
  completedSteps: number;
  failedSteps: number;
  activeKeys: number;
}

export interface RecentActivity {
  id: string;
  type: "workflow_created" | "step_completed" | "step_failed" | "key_created";
  label: string;
  meta: string;
  timestamp: string;
  status?: "completed" | "failed" | "pending" | "running";
}

export const DUMMY_STATS: DashboardStats = {
  totalWorkflows: 14,
  pendingSteps: 3,
  completedSteps: 128,
  failedSteps: 2,
  activeKeys: 2,
};

export const DUMMY_ACTIVITY: RecentActivity[] = [
  {
    id: "act-1",
    type: "step_completed",
    label: "image-resize completed",
    meta: "Workflow: media-pipeline",
    timestamp: "2 min ago",
    status: "completed",
  },
  {
    id: "act-2",
    type: "step_failed",
    label: "send-notification failed",
    meta: "Workflow: user-onboarding — attempt 3/3",
    timestamp: "18 min ago",
    status: "failed",
  },
  {
    id: "act-3",
    type: "workflow_created",
    label: "Workflow created",
    meta: "data-export — queued 6 steps",
    timestamp: "1 hr ago",
    status: "pending",
  },
  {
    id: "act-4",
    type: "step_completed",
    label: "validate-input completed",
    meta: "Workflow: user-onboarding",
    timestamp: "2 hr ago",
    status: "completed",
  },
  {
    id: "act-5",
    type: "key_created",
    label: "New project key created",
    meta: "Worker Prod Key • af3x_••••••••",
    timestamp: "Yesterday",
    status: "completed",
  },
];
