"use client";

import { HardDrive } from "lucide-react";

interface DataRetentionSectionProps {
  retentionDays: number;
  setRetentionDays: (val: number) => void;
  usedBytesMB?: number;
  capBytesGB?: number;
}

export function DataRetentionSection({
  retentionDays,
  setRetentionDays,
  usedBytesMB = 4.2,
  capBytesGB = 10.0,
}: DataRetentionSectionProps) {
  const percent = Math.min(100, Math.max(0.1, (usedBytesMB / (capBytesGB * 1024)) * 100));

  return (
    <div className="rounded-xl border border-white/10 bg-[#161620] p-6 space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
          <HardDrive size={16} className="text-blue-400" />
          Data Retention & Telemetry Storage
        </h3>
        <p className="text-xs text-zinc-400 mt-1">
          Configure auto-purge retention policies for workflow executions and step payloads.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Execution History Retention</label>
          <select
            value={retentionDays}
            onChange={(e) => setRetentionDays(parseInt(e.target.value))}
            className="w-full h-9 rounded-md bg-[#1b1b26] border border-white/10 text-zinc-100 text-xs px-3 focus:border-violet-500 focus:outline-none"
          >
            <option value={7}>7 Days (Recommended for dev)</option>
            <option value={30}>30 Days (Standard)</option>
            <option value={90}>90 Days (Compliance Extended)</option>
            <option value={0}>Unlimited (Keep indefinitely)</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Telemetry Storage Utilization</label>
          <div className="p-3 rounded-md bg-[#12121a] border border-white/10 space-y-2">
            <div className="flex justify-between text-xs text-zinc-300 font-mono">
              <span>Used: {usedBytesMB.toFixed(1)} MB</span>
              <span>Cap: {capBytesGB.toFixed(1)} GB</span>
            </div>
            <div className="w-full bg-white/10 h-1.5 rounded-full overflow-hidden">
              <div className="bg-violet-500 h-full transition-all" style={{ width: `${percent}%` }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
