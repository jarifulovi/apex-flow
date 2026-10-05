"use client";

import { Input } from "@/components/ui/input";
import { Zap } from "lucide-react";

interface ExecutionPolicySectionProps {
  maxRetries: number;
  setMaxRetries: (val: number) => void;
  lockTimeoutSeconds: number;
  setLockTimeoutSeconds: (val: number) => void;
  concurrencyLimit: number;
  setConcurrencyLimit: (val: number) => void;
  payloadTracingMode: "full" | "truncated" | "masked";
  setPayloadTracingMode: (val: "full" | "truncated" | "masked") => void;
}

export function ExecutionPolicySection({
  maxRetries,
  setMaxRetries,
  lockTimeoutSeconds,
  setLockTimeoutSeconds,
  concurrencyLimit,
  setConcurrencyLimit,
  payloadTracingMode,
  setPayloadTracingMode,
}: ExecutionPolicySectionProps) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#161620] p-6 space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
          <Zap size={16} className="text-amber-400" />
          Workflow & Step Execution Policy
        </h3>
        <p className="text-xs text-zinc-400 mt-1">
          Default behavior for steps and workers when explicit values are omitted in SDK step definitions.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Default Max Retry Attempts</label>
          <div className="flex items-center gap-3">
            <Input
              type="number"
              min={1}
              max={10}
              value={maxRetries}
              onChange={(e) => setMaxRetries(parseInt(e.target.value) || 1)}
              className="bg-[#1b1b26] border-white/10 text-zinc-100 text-xs focus:border-violet-500 w-32"
            />
            <span className="text-xs text-zinc-400">attempts before marking step as failed</span>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Step Lock Timeout</label>
          <div className="flex items-center gap-3">
            <Input
              type="number"
              min={10}
              max={600}
              value={lockTimeoutSeconds}
              onChange={(e) => setLockTimeoutSeconds(parseInt(e.target.value) || 30)}
              className="bg-[#1b1b26] border-white/10 text-zinc-100 text-xs focus:border-violet-500 w-32"
            />
            <span className="text-xs text-zinc-400">seconds before re-queuing crashed steps</span>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Sub-Workflow Concurrency Limit</label>
          <div className="flex items-center gap-3">
            <Input
              type="number"
              min={5}
              max={500}
              value={concurrencyLimit}
              onChange={(e) => setConcurrencyLimit(parseInt(e.target.value) || 10)}
              className="bg-[#1b1b26] border-white/10 text-zinc-100 text-xs focus:border-violet-500 w-32"
            />
            <span className="text-xs text-zinc-400">max active workflows per project</span>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Payload Tracing Mode</label>
          <select
            value={payloadTracingMode}
            onChange={(e) => setPayloadTracingMode(e.target.value as any)}
            className="w-full h-9 rounded-md bg-[#1b1b26] border border-white/10 text-zinc-100 text-xs px-3 focus:border-violet-500 focus:outline-none"
          >
            <option value="full">Full (Capture complete input & output JSON)</option>
            <option value="truncated">Truncated (Cap payloads at 10KB per step)</option>
            <option value="masked">Masked (Auto-sanitize sensitive key strings)</option>
          </select>
        </div>
      </div>
    </div>
  );
}
