import type { WorkflowDetail, WorkflowStepSummary } from "./api";

const tenMinsAgo = new Date(Date.now() - 600000).toISOString();
const fiveMinsAgo = new Date(Date.now() - 300000).toISOString();

function createDummyStep(
  order: number,
  name: string,
  status: WorkflowStepSummary["status"],
  errorMsg?: string | null,
  attempts = 1
): WorkflowStepSummary {
  return {
    id: `step-mock-${order}`,
    workflow_run_id: "mock-wf-run-101",
    step_name: name,
    step_order: order,
    status,
    attempt_count: attempts,
    max_attempts: 3,
    input_payload: { order_id: `ORD-${order}`, batch_index: order, env: "production" },
    output_payload: status === "success" ? { status: "processed", processed_items: 250, execution_time_ms: 120 } : {},
    error_message: errorMsg || null,
    started_at: tenMinsAgo,
    completed_at: status === "success" || status === "failed" ? fiveMinsAgo : null,
    created_at: tenMinsAgo,
    updated_at: fiveMinsAgo,
  };
}

// Case 1: Sequence of 5 continuous success steps (< 10)
const group1: WorkflowStepSummary[] = [
  createDummyStep(1, "validate-schema", "success"),
  createDummyStep(2, "auth-verify-key", "success"),
  createDummyStep(3, "parse-payload-header", "success"),
  createDummyStep(4, "check-rate-limit", "success"),
  createDummyStep(5, "sanitize-input", "success"),
];

// Case 2: Single failure step in the middle (Pinned & Expanded)
const failureStep = createDummyStep(
  6,
  "reserve-inventory-lock",
  "failed",
  "SKU #KB-809 OUT_OF_STOCK: Warehouse WH-EAST-04 reports 0 available units for allocation",
  2
);

// Case 3: Large sequence of 14 continuous success steps (> 10)
const group2: WorkflowStepSummary[] = Array.from({ length: 14 }, (_, i) => {
  const stepNum = 7 + i;
  return createDummyStep(stepNum, `process-batch-chunk-${i + 1}`, "success");
});

// Case 4: Running step (Pinned & Animated)
const runningStep = createDummyStep(21, "dispatch-carrier-webhook", "running", null, 1);

// Case 5: Final sequence of 3 continuous success steps
const group3: WorkflowStepSummary[] = [
  createDummyStep(22, "generate-pdf-invoice", "success"),
  createDummyStep(23, "upload-s3-archive", "success"),
  createDummyStep(24, "send-completion-email", "success"),
];

// Case 6: Consecutive failure steps (Each pinned & expanded individually in sequence)
const consecutiveFailures: WorkflowStepSummary[] = [
  createDummyStep(
    25,
    "notify-slack-alert-channel",
    "failed",
    "Webhook HTTP 500: Internal Server Error from Slack Gateway API",
    3
  ),
  createDummyStep(
    26,
    "push-datadog-metric-event",
    "failed",
    "Connection Timeout: DataDog API endpoint api.datadoghq.com unresponsive",
    3
  ),
  createDummyStep(
    27,
    "trigger-pagerduty-incident",
    "failed",
    "Authentication Error: Invalid PagerDuty API integration key",
    1
  ),
];

export const MOCK_WORKFLOW_DETAIL: WorkflowDetail = {
  id: "4782faec-4e8d-48ab-82cc-4b4dfc691a06",
  project_id: "proj-demo-apex",
  workflow_name: "ecommerce-order-pipeline",
  status: "failed",
  metadata: {
    customer_id: "CUST-9921",
    region: "us-east-1",
    simulation_mode: true,
  },
  deduplication_id: "order-ord-43b8a6-v1",
  parent_workflow_id: null,
  started_at: tenMinsAgo,
  completed_at: fiveMinsAgo,
  steps_count: 27,
  created_at: tenMinsAgo,
  updated_at: fiveMinsAgo,
  steps: [...group1, failureStep, ...group2, runningStep, ...group3, ...consecutiveFailures],
};
