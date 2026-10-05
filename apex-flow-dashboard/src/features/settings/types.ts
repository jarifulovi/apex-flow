export interface ProjectGeneralSettings {
  name: string;
  environment: "Production" | "Staging" | "Development";
  region: string;
  description: string;
}

export interface ExecutionPolicySettings {
  maxRetries: number;
  lockTimeoutSeconds: number;
  concurrencyLimit: number;
  payloadTracingMode: "full" | "truncated" | "masked";
}

export interface WebhookAlertSettings {
  webhookUrl: string;
  alertOnFailure: boolean;
  alertOnMaxRetry: boolean;
  alertOnWorkerDisconnect: boolean;
}

export interface DataRetentionSettings {
  retentionDays: number;
  usedBytesMB: number;
  capBytesGB: number;
}
