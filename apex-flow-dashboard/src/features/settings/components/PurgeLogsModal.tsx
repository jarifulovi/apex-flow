"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ShieldAlert, Trash2, Loader2 } from "lucide-react";

interface PurgeLogsModalProps {
  isOpen: boolean;
  projectName?: string;
  onClose: () => void;
  onConfirm: () => void;
}

export function PurgeLogsModal({ isOpen, projectName, onClose, onConfirm }: PurgeLogsModalProps) {
  const [purging, setPurging] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = () => {
    setPurging(true);
    setTimeout(() => {
      setPurging(false);
      onConfirm();
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#161620] border border-red-500/30 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
        <div className="flex items-center gap-3 text-red-400">
          <ShieldAlert size={22} />
          <h3 className="font-semibold text-sm">Purge Execution Logs Confirmation</h3>
        </div>
        <p className="text-xs text-zinc-300 leading-relaxed">
          Are you sure you want to delete all completed, cancelled, or failed execution logs for{" "}
          <strong className="text-white">{projectName || "this project"}</strong>? This will clear workflow step history.
        </p>
        <div className="flex justify-end gap-3 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="border-white/10 bg-[#1b1b26] text-zinc-300 text-xs"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleConfirm}
            disabled={purging}
            className="bg-red-600 hover:bg-red-500 text-white text-xs gap-1.5"
          >
            {purging ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
            <span>{purging ? "Purging..." : "Confirm Purge"}</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
