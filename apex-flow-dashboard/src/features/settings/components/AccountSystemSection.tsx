"use client";

import { useState } from "react";
import { User, Copy, Check, Server, Database } from "lucide-react";

interface AccountSystemSectionProps {
  userEmail?: string;
  userId?: string;
}

export function AccountSystemSection({ userEmail, userId }: AccountSystemSectionProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const id = userId || "cd29ac16-217f-4a91-b0e9-3da7534434b0";
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-white/10 bg-[#161620] p-6 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <User size={16} className="text-violet-400" />
            Authenticated User Account
          </h3>
          <p className="text-xs text-zinc-400 mt-1">
            Supabase Authentication identity and active user session info.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-1.5">
            <span className="text-xs text-zinc-400">Email Address</span>
            <div className="text-sm font-medium text-zinc-100">{userEmail || "developer@apexflow.dev"}</div>
          </div>

          <div className="space-y-1.5">
            <span className="text-xs text-zinc-400">User ID (`sub`)</span>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-zinc-300 truncate max-w-[220px]">
                {userId || "cd29ac16-217f-4a91-b0e9-3da7534434b0"}
              </span>
              <button onClick={handleCopy} className="text-zinc-400 hover:text-white">
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-[#161620] p-6 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <Server size={16} className="text-emerald-400" />
            Control Plane Engine System Status
          </h3>
          <p className="text-xs text-zinc-400 mt-1">FastAPI Orchestrator engine environment metrics.</p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3 rounded-lg bg-[#12121a] border border-white/10">
            <div className="text-[11px] text-zinc-400">System Version</div>
            <div className="text-xs font-semibold text-zinc-100 font-mono mt-0.5">v1.4.0-GA</div>
          </div>

          <div className="p-3 rounded-lg bg-[#12121a] border border-white/10">
            <div className="text-[11px] text-zinc-400">API Endpoint</div>
            <div className="text-xs font-semibold text-violet-300 font-mono mt-0.5">http://127.0.0.1:8000</div>
          </div>

          <div className="p-3 rounded-lg bg-[#12121a] border border-white/10">
            <div className="text-[11px] text-zinc-400">Database Backend</div>
            <div className="text-xs font-semibold text-emerald-400 font-mono mt-0.5 flex items-center gap-1">
              <Database size={12} /> PostgreSQL
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[#12121a] border border-white/10">
            <div className="text-[11px] text-zinc-400">SDK Spec Version</div>
            <div className="text-xs font-semibold text-cyan-300 font-mono mt-0.5">2026.10</div>
          </div>
        </div>
      </div>
    </div>
  );
}
