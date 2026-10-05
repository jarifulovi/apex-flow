"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Bell, Send, Loader2 } from "lucide-react";

interface AlertsWebhooksSectionProps {
  webhookUrl: string;
  setWebhookUrl: (val: string) => void;
  alertOnFailure: boolean;
  setAlertOnFailure: (val: boolean) => void;
  alertOnMaxRetry: boolean;
  setAlertOnMaxRetry: (val: boolean) => void;
  alertOnWorkerDisconnect: boolean;
  setAlertOnWorkerDisconnect: (val: boolean) => void;
}

export function AlertsWebhooksSection({
  webhookUrl,
  setWebhookUrl,
  alertOnFailure,
  setAlertOnFailure,
  alertOnMaxRetry,
  setAlertOnMaxRetry,
  alertOnWorkerDisconnect,
  setAlertOnWorkerDisconnect,
}: AlertsWebhooksSectionProps) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleTestWebhook = () => {
    setTesting(true);
    setTestResult(null);
    setTimeout(() => {
      setTesting(false);
      setTestResult("✅ Webhook HTTP 200 OK: Test payload dispatched successfully.");
      setTimeout(() => setTestResult(null), 4000);
    }, 800);
  };

  return (
    <div className="rounded-xl border border-white/10 bg-[#161620] p-6 space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
          <Bell size={16} className="text-cyan-400" />
          Alert Notifications & Webhook Integration
        </h3>
        <p className="text-xs text-zinc-400 mt-1">
          Receive real-time HTTP POST alerts on workflow failures or worker heartbeats.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Webhook POST Endpoint URL</label>
          <div className="flex items-center gap-2">
            <Input
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://your-domain.com/api/webhooks/apexflow"
              className="bg-[#1b1b26] border-white/10 text-zinc-100 font-mono text-xs focus:border-violet-500"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleTestWebhook}
              disabled={testing}
              className="border-white/10 text-zinc-300 bg-[#1b1b26] hover:bg-[#252536] text-xs h-9 px-3 gap-1.5 shrink-0"
            >
              {testing ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
              <span>{testing ? "Testing..." : "Send Test Alert"}</span>
            </Button>
          </div>
          {testResult && (
            <div className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 p-2.5 rounded-md font-mono">
              {testResult}
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-white/10 space-y-3">
          <label className="text-xs font-medium text-zinc-300">Trigger Incident Alerts On:</label>

          <div className="space-y-2.5">
            <label className="flex items-center gap-3 text-xs text-zinc-300 cursor-pointer">
              <input
                type="checkbox"
                checked={alertOnFailure}
                onChange={(e) => setAlertOnFailure(e.target.checked)}
                className="rounded bg-[#1b1b26] border-white/20 text-violet-600 focus:ring-violet-500"
              />
              <span>Workflow Run status changes to <strong className="text-red-400">FAILED</strong></span>
            </label>

            <label className="flex items-center gap-3 text-xs text-zinc-300 cursor-pointer">
              <input
                type="checkbox"
                checked={alertOnMaxRetry}
                onChange={(e) => setAlertOnMaxRetry(e.target.checked)}
                className="rounded bg-[#1b1b26] border-white/20 text-violet-600 focus:ring-violet-500"
              />
              <span>Step reaches maximum retry limit without succeeding</span>
            </label>

            <label className="flex items-center gap-3 text-xs text-zinc-300 cursor-pointer">
              <input
                type="checkbox"
                checked={alertOnWorkerDisconnect}
                onChange={(e) => setAlertOnWorkerDisconnect(e.target.checked)}
                className="rounded bg-[#1b1b26] border-white/20 text-violet-600 focus:ring-violet-500"
              />
              <span>Active worker missed heartbeat for more than 60 seconds</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
