"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Building2, Copy, Check, AlertTriangle, Trash2, Loader2, ShieldAlert } from "lucide-react";

interface GeneralSettingsSectionProps {
  projectId?: string;
  projectName: string;
  setProjectName: (val: string) => void;
  isDefaultProject: boolean;
  onOpenPurgeModal: () => void;
  onDeleteProject: () => Promise<void>;
}

export function GeneralSettingsSection({
  projectId,
  projectName,
  setProjectName,
  isDefaultProject,
  onOpenPurgeModal,
  onDeleteProject,
}: GeneralSettingsSectionProps) {
  const [copied, setCopied] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleCopy = () => {
    if (!projectId) return;
    navigator.clipboard.writeText(projectId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleConfirmDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await onDeleteProject();
      setShowDeleteModal(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to delete project.";
      setDeleteError(message);
    } finally {
      setDeleting(false);
    }
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
            General project identifier and display name used across your workspace.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-300">Project Name</label>
            <Input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              maxLength={100}
              className="bg-[#1b1b26] border-white/10 text-zinc-100 text-xs focus:border-violet-500"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-300">Project ID (UUID)</label>
            <div className="flex items-center gap-2">
              <Input
                readOnly
                value={projectId || ""}
                className="bg-[#12121a] border-white/10 text-zinc-400 font-mono text-xs"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                disabled={!projectId}
                className="border-white/10 text-zinc-300 bg-[#1b1b26] hover:bg-[#252536] text-xs h-9 px-3 gap-1.5"
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </Button>
            </div>
          </div>
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

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-3 border-t border-red-500/10">
          <div>
            <div className="text-xs font-medium text-zinc-200">Purge Finished Execution History</div>
            <div className="text-[11px] text-zinc-400">
              Deletes completed, failed, and cancelled workflow runs and step logs for this project.
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

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-3 border-t border-red-500/10">
          <div>
            <div className="text-xs font-medium text-zinc-200">Delete Project</div>
            <div className="text-[11px] text-zinc-400">
              {isDefaultProject
                ? "The Default Project cannot be deleted."
                : "Permanently deletes this project, API keys, workers, and all workflow runs."}
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={isDefaultProject || !projectId}
            onClick={() => {
              setDeleteError(null);
              setShowDeleteModal(true);
            }}
            className="border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-300 disabled:opacity-40 disabled:cursor-not-allowed text-xs gap-1.5 shrink-0"
          >
            <Trash2 size={13} />
            <span>Delete Project</span>
          </Button>
        </div>
      </div>

      {showDeleteModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#161620] border border-red-500/30 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400">
              <ShieldAlert size={22} />
              <h3 className="font-semibold text-sm">Delete Project Confirmation</h3>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed">
              Are you sure you want to permanently delete{" "}
              <strong className="text-white">{projectName || "this project"}</strong>? All API keys,
              workers, workflow runs, and step logs will be removed immediately.
            </p>
            {deleteError && (
              <div className="p-2.5 rounded-md bg-red-500/10 border border-red-500/30 text-red-300 text-xs">
                {deleteError}
              </div>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDeleteModal(false)}
                disabled={deleting}
                className="border-white/10 bg-[#1b1b26] text-zinc-300 text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleConfirmDelete}
                disabled={deleting}
                className="bg-red-600 hover:bg-red-500 text-white text-xs gap-1.5"
              >
                {deleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                <span>{deleting ? "Deleting..." : "Confirm Delete"}</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
