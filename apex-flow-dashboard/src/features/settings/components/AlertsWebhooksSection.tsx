"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Bell, Send, Loader2, ShieldAlert } from "lucide-react";
import type { AlertWindowSeconds, MaxAlertsPerWindow } from "../types";
import type { WebhookTestResponse } from "@/features/projects/types";

interface AlertsWebhooksSectionProps {
  webhookUrl: string;
  setWebhookUrl: (val: string) => void;
  alertOnFailure: boolean;
  setAlertOnFailure: (val: boolean) => void;
  alertOnTimeout: boolean;
  setAlertOnTimeout: (val: boolean) => void;
  alertOnMaxRetry: boolean;
  setAlertOnMaxRetry: (val: boolean) => void;
  windowSeconds: AlertWindowSeconds;
  setWindowSeconds: (val: AlertWindowSeconds) => void;
  maxAlertsPerWindow: MaxAlertsPerWindow;
  setMaxAlertsPerWindow: (val: MaxAlertsPerWindow) => void;
  onTestWebhook: () => Promise<WebhookTestResponse>;
}

export function AlertsWebhooksSection({
  webhookUrl,
  setWebhookUrl,
  alertOnFailure,
  setAlertOnFailure,
  alertOnTimeout,
  setAlertOnTimeout,
  alertOnMaxRetry,
  setAlertOnMaxRetry,
  windowSeconds,
  setWindowSeconds,
  maxAlertsPerWindow,
  setMaxAlertsPerWindow,
  onTestWebhook,
}: AlertsWebhooksSectionProps) {
  const [testing, setTesting] = useState(false);
  const [testFeedback, setTestFeedback] = useState<{ ok: boolean; message: string } | null>(null);

  const handleTestWebhook = async () => {
    setTesting(true);
    setTestFeedback(null);
    try {
      const result = await onTestWebhook();
      if (result.ok) {
        setTestFeedback({
          ok: true,
          message: `${result.detail} (${result.latency_ms}ms)`,
        });
      } else {
        setTestFeedback({
          ok: false,
          message: `${result.detail} (${result.latency_ms}ms)`,
        });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to send test alert.";
      setTestFeedback({
        ok: false,
        message,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="rounded-xl border border-white/10 bg-[#161620] p-6 space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
          <Bell size={16} className="text-cyan-400" />
          Alert Notifications &amp; Webhook Integration
        </h3>
        <p className="text-xs text-zinc-400 mt-1">
          Receive real-time Slack, Discord, or HTTP POST alerts on terminal workflow failures and timeouts.
        </p>
      </div>

      <div className="space-y-6">
        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Webhook POST Endpoint URL</label>
          <div className="flex items-center gap-2">
            <Input
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/... or https://discord.com/api/webhooks/..."
              className="bg-[#1b1b26] border-white/10 text-zinc-100 font-mono text-xs focus:border-violet-500"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleTestWebhook}
              disabled={testing || !webhookUrl.trim()}
              className="border-white/10 text-zinc-300 bg-[#1b1b26] hover:bg-[#252536] text-xs h-9 px-3 gap-1.5 shrink-0"
            >
              {testing ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
              <span>{testing ? "Testing..." : "Send Test Alert"}</span>
            </Button>
          </div>
          <p className="text-[11px] text-zinc-400">
            Payload format is automatically tailored for Slack Block Kit, Discord Embeds, or standard JSON webhooks.
          </p>
          {testFeedback && (
            <div
              className={`text-xs p-2.5 rounded-md font-mono border ${
                testFeedback.ok
                  ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                  : "text-red-400 bg-red-500/10 border-red-500/20"
              }`}
            >
              {testFeedback.ok ? "✅ " : "❌ "}
              {testFeedback.message}
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-white/10 space-y-4">
          <div>
            <h4 className="text-xs font-medium text-zinc-200 flex items-center gap-1.5">
              <ShieldAlert size={14} className="text-amber-400" />
              Sliding Window Rate Limit (Anti-Hammering)
            </h4>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Limits alerts per workflow within the sliding window and coalesces excess incidents into a single digest summary when the window expires.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Sliding Window Duration</label>
              <select
                value={windowSeconds}
                onChange={(e) => setWindowSeconds(Number(e.target.value) as AlertWindowSeconds)}
                className="w-full h-9 rounded-md bg-[#1b1b26] border border-white/10 text-zinc-100 text-xs px-3 focus:border-violet-500 focus:outline-none"
              >
                <option value={60}>1 Minute</option>
                <option value={300}>5 Minutes (Recommended)</option>
                <option value={900}>15 Minutes</option>
                <option value={1800}>30 Minutes</option>
                <option value={3600}>1 Hour</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Max Alerts per Workflow in Window</label>
              <select
                value={maxAlertsPerWindow}
                onChange={(e) => setMaxAlertsPerWindow(Number(e.target.value) as MaxAlertsPerWindow)}
                className="w-full h-9 rounded-md bg-[#1b1b26] border border-white/10 text-zinc-100 text-xs px-3 focus:border-violet-500 focus:outline-none"
              >
                <option value={1}>1 Alert per window (Strict)</option>
                <option value={3}>3 Alerts per window (Recommended)</option>
                <option value={5}>5 Alerts per window</option>
                <option value={10}>10 Alerts per window</option>
              </select>
            </div>
          </div>
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
              <span>
                Workflow Run status changes to <strong className="text-red-400">FAILED</strong>
              </span>
            </label>

            <label className="flex items-center gap-3 text-xs text-zinc-300 cursor-pointer">
              <input
                type="checkbox"
                checked={alertOnTimeout}
                onChange={(e) => setAlertOnTimeout(e.target.checked)}
                className="rounded bg-[#1b1b26] border-white/20 text-violet-600 focus:ring-violet-500"
              />
              <span>Workflow Execution times out (deadline_at / step lock expired)</span>
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

            <label className="flex items-center gap-3 text-xs text-zinc-500 cursor-not-allowed">
              <input
                type="checkbox"
                checked={false}
                disabled={true}
                onChange={() => {}}
                className="rounded bg-[#1b1b26] border-white/10 text-zinc-600 opacity-50 cursor-not-allowed"
              />
              <span>Active worker missed heartbeat for more than 60 seconds</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-zinc-400">
                Deferred / Coming Soon
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
