export type AlertWindowSeconds = 60 | 300 | 900 | 1800 | 3600;
export type MaxAlertsPerWindow = 1 | 3 | 5 | 10;

export interface ProjectGeneralSettings {
  name: string;
}

export interface WebhookAlertSettings {
  webhookUrl: string;
  alertOnFailure: boolean;
  alertOnTimeout: boolean;
  alertOnMaxRetry: boolean;
  alertOnWorkerDisconnect: boolean;
  windowSeconds: AlertWindowSeconds;
  maxAlertsPerWindow: MaxAlertsPerWindow;
}
