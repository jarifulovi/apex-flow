"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/shared/Header";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import { Button } from "@/components/ui/button";
import {
  Building2,
  Zap,
  Bell,
  HardDrive,
  User,
  Check,
  Save,
  Loader2,
} from "lucide-react";

import {
  MOCK_SETTINGS,
  GeneralSettingsSection,
  ExecutionPolicySection,
  AlertsWebhooksSection,
  DataRetentionSection,
  AccountSystemSection,
  PurgeLogsModal,
} from "@/features/settings";

type SettingsTab = "general" | "execution" | "alerts" | "retention" | "account";

export default function SettingsPage() {
  const { user } = useAuth();
  const { currentProject } = useProject();

  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // General Settings Form State
  const [projectName, setProjectName] = useState(MOCK_SETTINGS.general.name);
  const [environment, setEnvironment] = useState<string>(MOCK_SETTINGS.general.environment);
  const [region, setRegion] = useState(MOCK_SETTINGS.general.region);
  const [description, setDescription] = useState(MOCK_SETTINGS.general.description);

  // Execution Defaults Form State
  const [maxRetries, setMaxRetries] = useState(MOCK_SETTINGS.execution.maxRetries);
  const [lockTimeoutSeconds, setLockTimeoutSeconds] = useState(MOCK_SETTINGS.execution.lockTimeoutSeconds);
  const [concurrencyLimit, setConcurrencyLimit] = useState(MOCK_SETTINGS.execution.concurrencyLimit);
  const [payloadTracingMode, setPayloadTracingMode] = useState<"full" | "truncated" | "masked">(
    MOCK_SETTINGS.execution.payloadTracingMode
  );

  // Webhook Alerting Form State
  const [webhookUrl, setWebhookUrl] = useState(MOCK_SETTINGS.alerts.webhookUrl);
  const [alertOnFailure, setAlertOnFailure] = useState(MOCK_SETTINGS.alerts.alertOnFailure);
  const [alertOnMaxRetry, setAlertOnMaxRetry] = useState(MOCK_SETTINGS.alerts.alertOnMaxRetry);
  const [alertOnWorkerDisconnect, setAlertOnWorkerDisconnect] = useState(
    MOCK_SETTINGS.alerts.alertOnWorkerDisconnect
  );

  // Retention Form State
  const [retentionDays, setRetentionDays] = useState(MOCK_SETTINGS.retention.retentionDays);

  // Modals
  const [showPurgeModal, setShowPurgeModal] = useState(false);
  const [purgeSuccess, setPurgeSuccess] = useState(false);

  // Initialize with real project data when currentProject is available
  useEffect(() => {
    if (currentProject) {
      setProjectName(currentProject.name);
    }
  }, [currentProject]);

  const handleSaveSettings = () => {
    setSaving(true);
    setSaveSuccess(false);
    setTimeout(() => {
      setSaving(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    }, 600);
  };

  const handlePurgeConfirm = () => {
    setShowPurgeModal(false);
    setPurgeSuccess(true);
    setTimeout(() => setPurgeSuccess(false), 3000);
  };

  return (
    <div className="dashboard-page">
      <Header
        title="Project & Control Plane Settings"
        subtitle={`Configure defaults, webhook alerts, data retention, and settings for ${currentProject?.name || "your project"}`}
        actions={
          <Button
            onClick={handleSaveSettings}
            disabled={saving}
            className="bg-violet-600 hover:bg-violet-500 text-white text-xs gap-1.5 shadow-lg shadow-violet-600/20"
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
        }
      />

      <div className="page-content space-y-6">
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
            onClick={() => setActiveTab("execution")}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "execution"
                ? "bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
            }`}
          >
            <Zap size={14} />
            <span>Execution Policy</span>
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
            <span>Alerts & Webhooks</span>
          </button>

          <button
            onClick={() => setActiveTab("retention")}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "retention"
                ? "bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
            }`}
          >
            <HardDrive size={14} />
            <span>Data Retention</span>
          </button>

          <button
            onClick={() => setActiveTab("account")}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "account"
                ? "bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
            }`}
          >
            <User size={14} />
            <span>Account & System</span>
          </button>
        </div>

        {/* Global Save Notification Banner */}
        {saveSuccess && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-200">
            <Check size={14} className="text-emerald-400" />
            <span>Project settings updated successfully.</span>
          </div>
        )}

        {purgeSuccess && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
            <Check size={14} className="text-emerald-400" />
            <span>Execution logs purged successfully.</span>
          </div>
        )}

        {/* Tab Sections */}
        {activeTab === "general" && (
          <GeneralSettingsSection
            projectId={currentProject?.id}
            projectName={projectName}
            setProjectName={setProjectName}
            environment={environment}
            setEnvironment={setEnvironment}
            region={region}
            setRegion={setRegion}
            description={description}
            setDescription={setDescription}
            onOpenPurgeModal={() => setShowPurgeModal(true)}
          />
        )}

        {activeTab === "execution" && (
          <ExecutionPolicySection
            maxRetries={maxRetries}
            setMaxRetries={setMaxRetries}
            lockTimeoutSeconds={lockTimeoutSeconds}
            setLockTimeoutSeconds={setLockTimeoutSeconds}
            concurrencyLimit={concurrencyLimit}
            setConcurrencyLimit={setConcurrencyLimit}
            payloadTracingMode={payloadTracingMode}
            setPayloadTracingMode={setPayloadTracingMode}
          />
        )}

        {activeTab === "alerts" && (
          <AlertsWebhooksSection
            webhookUrl={webhookUrl}
            setWebhookUrl={setWebhookUrl}
            alertOnFailure={alertOnFailure}
            setAlertOnFailure={setAlertOnFailure}
            alertOnMaxRetry={alertOnMaxRetry}
            setAlertOnMaxRetry={setAlertOnMaxRetry}
            alertOnWorkerDisconnect={alertOnWorkerDisconnect}
            setAlertOnWorkerDisconnect={setAlertOnWorkerDisconnect}
          />
        )}

        {activeTab === "retention" && (
          <DataRetentionSection
            retentionDays={retentionDays}
            setRetentionDays={setRetentionDays}
            usedBytesMB={MOCK_SETTINGS.retention.usedBytesMB}
            capBytesGB={MOCK_SETTINGS.retention.capBytesGB}
          />
        )}

        {activeTab === "account" && (
          <AccountSystemSection
            userEmail={user?.email}
            userId={user?.id}
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
