"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import {
  deleteProject,
  purgeProjectLogs,
  testProjectWebhook,
  updateProject,
} from "@/features/projects/api";
import { Button } from "@/components/ui/button";
import {
  Building2,
  Bell,
  Check,
  Save,
  Loader2,
  AlertCircle,
} from "lucide-react";

import {
  MOCK_SETTINGS,
  GeneralSettingsSection,
  AlertsWebhooksSection,
  PurgeLogsModal,
  type AlertWindowSeconds,
  type MaxAlertsPerWindow,
} from "@/features/settings";

type SettingsTab = "general" | "alerts";

const ALLOWED_WINDOW_SECONDS: readonly AlertWindowSeconds[] = [60, 300, 900, 1800, 3600];
const ALLOWED_MAX_ALERTS: readonly MaxAlertsPerWindow[] = [1, 3, 5, 10];

function pickPreset<T>(value: unknown, allowed: readonly T[], fallback: T): T {
  if (allowed.includes(value as T)) {
    return value as T;
  }
  return fallback;
}

export default function SettingsPage() {
  const { accessToken } = useAuth();
  const { currentProject, refreshProjects } = useProject();

  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // General Settings Form State
  const [projectName, setProjectName] = useState(MOCK_SETTINGS.general.name);

  // Webhook Alerting Form State
  const [webhookUrl, setWebhookUrl] = useState(MOCK_SETTINGS.alerts.webhookUrl);
  const [alertOnFailure, setAlertOnFailure] = useState(MOCK_SETTINGS.alerts.alertOnFailure);
  const [alertOnTimeout, setAlertOnTimeout] = useState(MOCK_SETTINGS.alerts.alertOnTimeout);
  const [alertOnMaxRetry, setAlertOnMaxRetry] = useState(MOCK_SETTINGS.alerts.alertOnMaxRetry);
  const [alertOnWorkerDisconnect, setAlertOnWorkerDisconnect] = useState(
    MOCK_SETTINGS.alerts.alertOnWorkerDisconnect
  );
  const [windowSeconds, setWindowSeconds] = useState<AlertWindowSeconds>(
    MOCK_SETTINGS.alerts.windowSeconds
  );
  const [maxAlertsPerWindow, setMaxAlertsPerWindow] = useState<MaxAlertsPerWindow>(
    MOCK_SETTINGS.alerts.maxAlertsPerWindow
  );

  // Modals & action banners
  const [showPurgeModal, setShowPurgeModal] = useState(false);
  const [purgeBanner, setPurgeBanner] = useState<string | null>(null);

  const isDefaultProject = Boolean(
    currentProject &&
      (currentProject.name === "Default Project" || currentProject.metadata?.is_default)
  );

  // Hydrate form state from persisted project & project.metadata
  useEffect(() => {
    if (!currentProject) return;

    const meta = currentProject.metadata || {};
    const alertsMeta = meta.alerts || {};

    setProjectName(currentProject.name);
    setWebhookUrl(typeof alertsMeta.webhook_url === "string" ? alertsMeta.webhook_url : "");
    setAlertOnFailure(
      typeof alertsMeta.alert_on_failure === "boolean"
        ? alertsMeta.alert_on_failure
        : MOCK_SETTINGS.alerts.alertOnFailure
    );
    setAlertOnTimeout(
      typeof alertsMeta.alert_on_timeout === "boolean"
        ? alertsMeta.alert_on_timeout
        : MOCK_SETTINGS.alerts.alertOnTimeout
    );
    setAlertOnMaxRetry(
      typeof alertsMeta.alert_on_max_retry === "boolean"
        ? alertsMeta.alert_on_max_retry
        : MOCK_SETTINGS.alerts.alertOnMaxRetry
    );
    setAlertOnWorkerDisconnect(
      typeof alertsMeta.alert_on_worker_disconnect === "boolean"
        ? alertsMeta.alert_on_worker_disconnect
        : MOCK_SETTINGS.alerts.alertOnWorkerDisconnect
    );
    setWindowSeconds(
      pickPreset(alertsMeta.window_seconds, ALLOWED_WINDOW_SECONDS, MOCK_SETTINGS.alerts.windowSeconds)
    );
    setMaxAlertsPerWindow(
      pickPreset(
        alertsMeta.max_alerts_per_window,
        ALLOWED_MAX_ALERTS,
        MOCK_SETTINGS.alerts.maxAlertsPerWindow
      )
    );
  }, [currentProject]);

  const handleSaveSettings = async () => {
    if (!accessToken || !currentProject) {
      setSaveError("Authentication or active project context missing.");
      return;
    }

    setSaving(true);
    setSaveSuccess(false);
    setSaveError(null);

    try {
      await updateProject(accessToken, currentProject.id, {
        name: projectName,
        alerts: {
          webhook_url: webhookUrl.trim(),
          alert_on_failure: alertOnFailure,
          alert_on_timeout: alertOnTimeout,
          alert_on_max_retry: alertOnMaxRetry,
          alert_on_worker_disconnect: alertOnWorkerDisconnect,
          window_seconds: windowSeconds,
          max_alerts_per_window: maxAlertsPerWindow,
        },
      });
      await refreshProjects();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save project settings.";
      setSaveError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleTestWebhook = async () => {
    if (!accessToken || !currentProject) {
      throw new Error("Authentication or active project context missing.");
    }
    return testProjectWebhook(accessToken, currentProject.id, webhookUrl.trim());
  };

  const handlePurgeConfirm = async () => {
    if (!accessToken || !currentProject) {
      throw new Error("Authentication or active project context missing.");
    }
    const res = await purgeProjectLogs(accessToken, currentProject.id);
    setPurgeBanner(`Purged ${res.deleted_runs} finished workflow run(s) successfully.`);
    setTimeout(() => setPurgeBanner(null), 4000);
  };

  const handleDeleteProject = async () => {
    if (!accessToken || !currentProject) {
      throw new Error("Authentication or active project context missing.");
    }
    await deleteProject(accessToken, currentProject.id);
    await refreshProjects();
  };

  return (
    <div className="dashboard-page p-6 space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-zinc-100">Project Settings</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Manage project identity, maintenance actions, and webhook alert notifications for{" "}
            {currentProject?.name || "your project"}
          </p>
        </div>
        <Button
          onClick={handleSaveSettings}
          disabled={saving || !currentProject}
          className="bg-violet-600 hover:bg-violet-500 text-white text-xs gap-1.5 shadow-lg shadow-violet-600/20 h-8 px-3"
        >
          {saving ? (
            <Loader2 size={13} className="animate-spin" />
          ) : saveSuccess ? (
            <Check size={13} className="text-emerald-300" />
          ) : (
            <Save size={13} />
          )}
          <span>{saving ? "Saving..." : saveSuccess ? "Saved!" : "Save Changes"}</span>
        </Button>
      </div>

      <div className="space-y-6">
        {/* Sub-Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 border-b border-white/10 pb-3">
          <button
            onClick={() => setActiveTab("general")}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "general"
                ? "bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
            }`}
          >
            <Building2 size={14} />
            <span>General</span>
          </button>

          <button
            onClick={() => setActiveTab("alerts")}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "alerts"
                ? "bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
            }`}
          >
            <Bell size={14} />
            <span>Alerts &amp; Webhooks</span>
          </button>
        </div>

        {/* Global Notification Banners */}
        {saveSuccess && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-200">
            <Check size={14} className="text-emerald-400" />
            <span>Project settings updated successfully.</span>
          </div>
        )}

        {saveError && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle size={14} className="text-red-400 shrink-0" />
            <span>{saveError}</span>
          </div>
        )}

        {purgeBanner && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
            <Check size={14} className="text-emerald-400" />
            <span>{purgeBanner}</span>
          </div>
        )}

        {/* Tab Sections */}
        {activeTab === "general" && (
          <GeneralSettingsSection
            projectId={currentProject?.id}
            projectName={projectName}
            setProjectName={setProjectName}
            isDefaultProject={isDefaultProject}
            onOpenPurgeModal={() => setShowPurgeModal(true)}
            onDeleteProject={handleDeleteProject}
          />
        )}

        {activeTab === "alerts" && (
          <AlertsWebhooksSection
            webhookUrl={webhookUrl}
            setWebhookUrl={setWebhookUrl}
            alertOnFailure={alertOnFailure}
            setAlertOnFailure={setAlertOnFailure}
            alertOnTimeout={alertOnTimeout}
            setAlertOnTimeout={setAlertOnTimeout}
            alertOnMaxRetry={alertOnMaxRetry}
            setAlertOnMaxRetry={setAlertOnMaxRetry}
            alertOnWorkerDisconnect={alertOnWorkerDisconnect}
            setAlertOnWorkerDisconnect={setAlertOnWorkerDisconnect}
            windowSeconds={windowSeconds}
            setWindowSeconds={setWindowSeconds}
            maxAlertsPerWindow={maxAlertsPerWindow}
            setMaxAlertsPerWindow={setMaxAlertsPerWindow}
            onTestWebhook={handleTestWebhook}
          />
        )}
      </div>

      {/* Modal Dialog */}
      <PurgeLogsModal
        isOpen={showPurgeModal}
        projectName={currentProject?.name}
        onClose={() => setShowPurgeModal(false)}
        onConfirm={handlePurgeConfirm}
      />
    </div>
  );
}
