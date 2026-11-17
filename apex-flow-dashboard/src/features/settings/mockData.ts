import type {
  ProjectGeneralSettings,
  WebhookAlertSettings,
} from "./types";

export const MOCK_SETTINGS: {
  general: ProjectGeneralSettings;
  alerts: WebhookAlertSettings;
} = {
  general: {
    name: "Default Project",
  },
  alerts: {
    webhookUrl: "",
    alertOnFailure: true,
    alertOnTimeout: true,
    alertOnMaxRetry: true,
    alertOnWorkerDisconnect: false,
    windowSeconds: 300,
    maxAlertsPerWindow: 3,
  },
};
