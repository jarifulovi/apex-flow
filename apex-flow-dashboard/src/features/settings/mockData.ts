import type {
  ProjectGeneralSettings,
  ExecutionPolicySettings,
  WebhookAlertSettings,
  DataRetentionSettings,
} from "./types";

export const MOCK_SETTINGS = {
  general: {
    name: "E-Commerce Pipeline",
    environment: "Production" as const,
    region: "us-east-1",
    description: "Main order processing and inventory orchestration pipeline.",
  },
  execution: {
    maxRetries: 3,
    lockTimeoutSeconds: 60,
    concurrencyLimit: 50,
    payloadTracingMode: "full" as const,
  },
  alerts: {
    webhookUrl: "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
    alertOnFailure: true,
    alertOnMaxRetry: true,
    alertOnWorkerDisconnect: false,
  },
  retention: {
    retentionDays: 30,
    usedBytesMB: 4.2,
    capBytesGB: 10.0,
  },
};
