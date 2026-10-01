// Dummy data for Steps — aligned to backend WorkflowStepResponse schema

export type StepStatus = "queued" | "running" | "success" | "failed";

export interface WorkflowStep {
  id: string;
  workflow_id: string;
  workflow_name?: string; // denormalized for display
  step_name: string;
  status: StepStatus;
  attempt_count: number;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export const DUMMY_STEPS: WorkflowStep[] = [
  {
    id: "step-001",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440001",
    workflow_name: "media-pipeline",
    step_name: "upload-to-s3",
    status: "success",
    attempt_count: 1,
    input_payload: { file: "avatar_user_42.png", size_kb: 420 },
    output_payload: { s3_key: "uploads/2026/09/avatar_user_42.png" },
    error_message: null,
    created_at: "2026-09-30T10:00:00Z",
    updated_at: "2026-09-30T10:01:30Z",
  },
  {
    id: "step-002",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440001",
    workflow_name: "media-pipeline",
    step_name: "image-resize",
    status: "success",
    attempt_count: 1,
    input_payload: { s3_key: "uploads/2026/09/avatar_user_42.png", widths: [64, 128, 512] },
    output_payload: { resized_keys: ["thumb_64.png", "thumb_128.png", "thumb_512.png"] },
    error_message: null,
    created_at: "2026-09-30T10:01:30Z",
    updated_at: "2026-09-30T10:03:00Z",
  },
  {
    id: "step-003",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440001",
    workflow_name: "media-pipeline",
    step_name: "cdn-invalidate",
    status: "running",
    attempt_count: 1,
    input_payload: { paths: ["/avatars/user_42/*"] },
    output_payload: {},
    error_message: null,
    created_at: "2026-09-30T10:03:00Z",
    updated_at: "2026-09-30T10:03:45Z",
  },
  {
    id: "step-004",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440002",
    workflow_name: "user-onboarding",
    step_name: "create-profile",
    status: "success",
    attempt_count: 1,
    input_payload: { user_id: "user-uuid-99", plan: "free" },
    output_payload: { profile_id: "prof-001" },
    error_message: null,
    created_at: "2026-09-30T08:00:00Z",
    updated_at: "2026-09-30T08:00:45Z",
  },
  {
    id: "step-005",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440002",
    workflow_name: "user-onboarding",
    step_name: "send-welcome-email",
    status: "success",
    attempt_count: 1,
    input_payload: { email: "newuser@example.com", template: "welcome_v2" },
    output_payload: { message_id: "ses-xyz-12345" },
    error_message: null,
    created_at: "2026-09-30T08:01:00Z",
    updated_at: "2026-09-30T08:01:22Z",
  },
  {
    id: "step-006",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440002",
    workflow_name: "user-onboarding",
    step_name: "send-notification",
    status: "failed",
    attempt_count: 3,
    input_payload: { channel: "slack", user_id: "user-uuid-99" },
    output_payload: {},
    error_message: "Slack API rate limit exceeded (429). Retry exhausted.",
    created_at: "2026-09-30T08:02:00Z",
    updated_at: "2026-09-30T08:15:00Z",
  },
  {
    id: "step-007",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440003",
    workflow_name: "payment-reconciliation",
    step_name: "fetch-invoices",
    status: "success",
    attempt_count: 1,
    input_payload: { month: "2026-09", limit: 500 },
    output_payload: { count: 487 },
    error_message: null,
    created_at: "2026-09-29T16:00:00Z",
    updated_at: "2026-09-29T16:03:00Z",
  },
  {
    id: "step-008",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440003",
    workflow_name: "payment-reconciliation",
    step_name: "match-transactions",
    status: "failed",
    attempt_count: 2,
    input_payload: { invoice_batch: "batch-2026-09" },
    output_payload: {},
    error_message: "Database connection timeout after 30s.",
    created_at: "2026-09-29T16:03:00Z",
    updated_at: "2026-09-29T16:22:00Z",
  },
  {
    id: "step-009",
    workflow_id: "wf-550e8400-e29b-41d4-a716-446655440004",
    workflow_name: "data-export",
    step_name: "build-report",
    status: "queued",
    attempt_count: 0,
    input_payload: { format: "csv", date_range: "2026-09" },
    output_payload: {},
    error_message: null,
    created_at: "2026-09-30T12:00:00Z",
    updated_at: "2026-09-30T12:00:00Z",
  },
];
