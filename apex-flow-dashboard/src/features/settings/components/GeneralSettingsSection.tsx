"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Building2, Copy, Check, AlertTriangle, Trash2 } from "lucide-react";

interface GeneralSettingsSectionProps {
  projectId?: string;
  projectName: string;
  setProjectName: (val: string) => void;
  environment: string;
  setEnvironment: (val: string) => void;
  region: string;
  setRegion: (val: string) => void;
  description: string;
  setDescription: (val: string) => void;
  onOpenPurgeModal: () => void;
}

export function GeneralSettingsSection({
  projectId,
  projectName,
  setProjectName,
  environment,
  setEnvironment,
  region,
  setRegion,
  description,
  setDescription,
  onOpenPurgeModal,
}: GeneralSettingsSectionProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const id = projectId || "b64a0476-14b6-454e-92bc-f6c98a68fff1";
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-white/10 bg-[#161620] p-6 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <Building2 size={16} className="text-violet-400" />
            Project Identity
          </h3>
          <p className="text-xs text-zinc-400 mt-1">
            General project metadata used across SDK initialization and control plane dashboard.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-300">Project Name</label>
            <Input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="bg-[#1b1b26] border-white/10 text-zinc-100 text-xs focus:border-violet-500"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-300">Environment Tag</label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="w-full h-9 rounded-md bg-[#1b1b26] border border-white/10 text-zinc-100 text-xs px-3 focus:border-violet-500 focus:outline-none"
            >
              <option value="Production">Production</option>
              <option value="Staging">Staging</option>
              <option value="Development">Development</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-300">Primary Region</label>
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="w-full h-9 rounded-md bg-[#1b1b26] border border-white/10 text-zinc-100 text-xs px-3 focus:border-violet-500 focus:outline-none"
            >
              <option value="us-east-1">us-east-1 (N. Virginia)</option>
              <option value="us-west-2">us-west-2 (Oregon)</option>
              <option value="eu-west-1">eu-west-1 (Ireland)</option>
              <option value="ap-southeast-1">ap-southeast-1 (Singapore)</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-300">Project ID (UUID)</label>
            <div className="flex items-center gap-2">
              <Input
                readOnly
                value={projectId || "b64a0476-14b6-454e-92bc-f6c98a68fff1"}
                className="bg-[#12121a] border-white/10 text-zinc-400 font-mono text-xs"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                className="border-white/10 text-zinc-300 bg-[#1b1b26] hover:bg-[#252536] text-xs h-9 px-3 gap-1.5"
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </Button>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full rounded-md bg-[#1b1b26] border border-white/10 text-zinc-100 text-xs p-3 focus:border-violet-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Danger Zone Card */}
      <div className="rounded-xl border border-red-500/20 bg-red-950/10 p-6 space-y-4">
        <div className="flex items-center gap-2 text-red-400 font-semibold text-sm">
          <AlertTriangle size={16} />
          <span>Danger Zone</span>
        </div>
        <p className="text-xs text-zinc-400">
          Destructive workspace maintenance operations. These actions cannot be undone.
        </p>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-2 border-t border-red-500/10">
          <div>
            <div className="text-xs font-medium text-zinc-200">Purge Finished Execution History</div>
            <div className="text-[11px] text-zinc-400">
              Removes completed and cancelled workflow runs and step logs for this project.
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenPurgeModal}
            className="border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-300 text-xs gap-1.5 shrink-0"
          >
            <Trash2 size={13} />
            <span>Purge Execution Logs</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
