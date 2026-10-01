// Dummy data for Workflows — aligned to backend WorkflowResponse & WorkflowDetailResponse

export type WorkflowStatus = "pending" | "running" | "completed" | "failed";

export interface Workflow {
  id: string;
  user_id: string;
  status: WorkflowStatus;
  metadata: {
    name?: string;
    description?: string;
    tags?: string[];
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
  steps_count?: number;
}

export const DUMMY_WORKFLOWS: Workflow[] = [
  {
    id: "wf-550e8400-e29b-41d4-a716-446655440001",
    user_id: "user-uuid-1",
    status: "running",
    metadata: {
      name: "media-pipeline",
      description: "Resize, compress and distribute uploaded images",
      tags: ["media", "image"],
    },
    created_at: "2026-09-30T10:00:00Z",
    updated_at: "2026-09-30T10:12:00Z",
    steps_count: 4,
  },
  {
    id: "wf-550e8400-e29b-41d4-a716-446655440002",
    user_id: "user-uuid-1",
    status: "completed",
    metadata: {
      name: "user-onboarding",
      description: "Send welcome email, create profile, assign free tier",
      tags: ["onboarding", "email"],
    },
    created_at: "2026-09-30T08:00:00Z",
    updated_at: "2026-09-30T08:34:00Z",
    steps_count: 6,
  },
  {
    id: "wf-550e8400-e29b-41d4-a716-446655440003",
    user_id: "user-uuid-1",
    status: "failed",
    metadata: {
      name: "payment-reconciliation",
      description: "Match and verify payment records against invoices",
      tags: ["billing", "finance"],
    },
    created_at: "2026-09-29T16:00:00Z",
    updated_at: "2026-09-29T16:22:00Z",
    steps_count: 3,
  },
  {
    id: "wf-550e8400-e29b-41d4-a716-446655440004",
    user_id: "user-uuid-1",
    status: "pending",
    metadata: {
      name: "data-export",
      description: "Export user analytics report to S3",
      tags: ["analytics", "export"],
    },
    created_at: "2026-09-30T12:00:00Z",
    updated_at: "2026-09-30T12:00:00Z",
    steps_count: 6,
  },
  {
    id: "wf-550e8400-e29b-41d4-a716-446655440005",
    user_id: "user-uuid-1",
    status: "completed",
    metadata: {
      name: "nightly-cleanup",
      description: "Purge stale sessions and expired tokens",
      tags: ["maintenance"],
    },
    created_at: "2026-09-29T00:00:00Z",
    updated_at: "2026-09-29T00:08:00Z",
    steps_count: 2,
  },
  {
    id: "wf-550e8400-e29b-41d4-a716-446655440006",
    user_id: "user-uuid-1",
    status: "running",
    metadata: {
      name: "report-generator",
      description: "Generate monthly PDF reports for all tenants",
      tags: ["reports", "pdf"],
    },
    created_at: "2026-09-30T11:00:00Z",
    updated_at: "2026-09-30T11:45:00Z",
    steps_count: 5,
  },
];
