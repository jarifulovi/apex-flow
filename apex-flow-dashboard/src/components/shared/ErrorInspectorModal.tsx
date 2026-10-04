"use client";

import React, { useState } from "react";
import { AlertTriangle, Copy, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorInspectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  stepName: string;
  errorMessage: string;
}

export function ErrorInspectorModal({
  isOpen,
  onClose,
  stepName,
  errorMessage,
}: ErrorInspectorModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(errorMessage);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="relative w-full max-w-2xl bg-[#161620] border border-red-500/30 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-red-950/30 border-b border-red-500/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/30">
              <AlertTriangle size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-100 font-mono">
                Error Details: {stepName}
              </h3>
              <p className="text-[11px] text-zinc-400">
                Step execution failure diagnostic trace
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/10 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Traceback Body */}
        <div className="p-6 overflow-y-auto space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider font-mono">
              Raw Error Message & Traceback
            </span>
            <Button
              onClick={handleCopy}
              variant="outline"
              size="sm"
              className="h-7 text-xs border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] gap-1.5"
            >
              {copied ? (
                <>
                  <Check size={12} className="text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy size={12} />
                  <span>Copy Error</span>
                </>
              )}
            </Button>
          </div>

          <pre className="p-4 bg-black/60 rounded-xl border border-white/10 text-red-300 text-xs font-mono leading-relaxed overflow-x-auto whitespace-pre-wrap break-words select-text max-h-[350px]">
            {errorMessage}
          </pre>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-[#111118] border-t border-white/5 flex justify-end">
          <Button
            onClick={onClose}
            variant="outline"
            size="sm"
            className="text-xs border-white/10 text-zinc-300 hover:text-white"
          >
            Close Inspector
          </Button>
        </div>
      </div>
    </div>
  );
}
