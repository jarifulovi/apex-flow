"use client";

import React from "react";
import { Cpu, Activity, Clock, ShieldCheck, AlertCircle } from "lucide-react";
import type { Worker } from "../types";

function formatLastSeen(iso: string | null): string {
  if (!iso) return "Never";
  const diffSec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diffSec < 10) return "Just now (<10s ago)";
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  return new Date(iso).toLocaleString();
}

function isAlive(iso: string | null): boolean {
  if (!iso) return false;
  const diffSec = (Date.now() - new Date(iso).getTime()) / 1000;
  return diffSec < 60; // Active heartbeat within 60s
}

export function WorkerList({ workers }: { workers: Worker[] }) {
  if (workers.length === 0) {
    return (
      <div className="table-empty">
        <Cpu size={28} className="table-empty-icon text-zinc-500" />
        <p className="table-empty-text">No active execution workers connected</p>
        <p className="table-empty-sub">
          Start your Python SDK worker using <code>client.start_worker()</code> to register workers here.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {workers.map((worker) => {
        const active = isAlive(worker.last_seen_at) && worker.status === "active";
        return (
          <div
            key={worker.id}
            className="bg-[#161620] border border-white/10 rounded-xl p-4 flex flex-col justify-between hover:border-violet-500/40 transition-all shadow-lg"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-violet-950/60 text-violet-400 border border-violet-500/30">
                    <Cpu size={16} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-100 font-mono">
                      {worker.name}
                    </h3>
                    <p className="text-[10px] text-zinc-500 font-mono">
                      ID: {worker.id.substring(0, 13)}...
                    </p>
                  </div>
                </div>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                    active
                      ? "bg-emerald-950/60 text-emerald-300 border border-emerald-500/30"
                      : "bg-zinc-800/60 text-zinc-400 border border-white/10"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      active ? "bg-emerald-400 animate-pulse" : "bg-zinc-500"
                    }`}
                  />
                  {active ? "Active Polling" : "Inactive / Idle"}
                </span>
              </div>

              <div className="space-y-2 mt-4 pt-3 border-t border-white/5 text-xs text-zinc-400">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Clock size={13} className="text-zinc-500" />
                    <span>Last Heartbeat:</span>
                  </span>
                  <span className="font-mono text-zinc-200">
                    {formatLastSeen(worker.last_seen_at)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck size={13} className="text-zinc-500" />
                    <span>Project Scope:</span>
                  </span>
                  <span className="font-mono text-zinc-400 text-[11px]">
                    {worker.project_id.substring(0, 8)}...
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-2 flex items-center justify-between text-[11px] text-zinc-500 border-t border-white/5">
              <span>Registered {new Date(worker.created_at).toLocaleDateString()}</span>
              {active ? (
                <span className="text-emerald-400 flex items-center gap-1 font-medium">
                  <Activity size={12} className="animate-spin" /> Live
                </span>
              ) : (
                <span className="text-zinc-500 flex items-center gap-1">
                  <AlertCircle size={12} /> Offline
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
