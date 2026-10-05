"use client";

import React, { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Check, Copy, FileCode2, Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface PayloadViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  payload: Record<string, unknown> | unknown;
}

export function PayloadViewerModal({
  isOpen,
  onClose,
  title = "Payload Inspection",
  payload,
}: PayloadViewerModalProps) {
  const [copied, setCopied] = useState(false);
  const [mode, setMode] = useState<"pretty" | "raw">("pretty");
  const [searchQuery, setSearchQuery] = useState("");

  const formattedJson = useMemo(() => {
    if (!payload || (typeof payload === "object" && Object.keys(payload as object).length === 0)) {
      return "{}";
    }
    try {
      return JSON.stringify(payload, null, mode === "pretty" ? 2 : undefined);
    } catch {
      return String(payload);
    }
  }, [payload, mode]);

  const filteredLines = useMemo(() => {
    const lines = formattedJson.split("\n");
    if (!searchQuery.trim()) return lines;
    const q = searchQuery.toLowerCase();
    return lines.filter((line) => line.toLowerCase().includes(q));
  }, [formattedJson, searchQuery]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJson);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy payload to clipboard:", err);
    }
  };

  const lineCount = formattedJson.split("\n").length;
  const byteSize = new Blob([formattedJson]).size;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-[#12121a] border-white/10 text-zinc-100 shadow-2xl backdrop-blur-xl p-0 gap-0 overflow-hidden rounded-xl sm:max-w-2xl">
        <DialogHeader className="p-4 bg-[#181824] border-b border-white/10 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-400">
              <FileCode2 size={16} />
            </div>
            <div>
              <DialogTitle className="text-sm font-semibold text-zinc-100">
                {title}
              </DialogTitle>
              <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                {lineCount} {lineCount === 1 ? "line" : "lines"} • {byteSize} bytes
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 mr-6">
            <div className="flex items-center bg-[#0d0d14] rounded-lg p-0.5 border border-white/10">
              <button
                onClick={() => setMode("pretty")}
                className={`px-2 py-1 text-[11px] font-medium rounded-md transition-colors ${
                  mode === "pretty"
                    ? "bg-violet-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Pretty
              </button>
              <button
                onClick={() => setMode("raw")}
                className={`px-2 py-1 text-[11px] font-medium rounded-md transition-colors ${
                  mode === "raw"
                    ? "bg-violet-600 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Raw
              </button>
            </div>

            <Button
              onClick={handleCopy}
              variant="outline"
              size="sm"
              className="h-7 text-xs bg-[#1b1b26] border-white/10 text-zinc-200 hover:text-white gap-1.5"
            >
              {copied ? (
                <>
                  <Check size={12} className="text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy size={12} />
                  <span>Copy</span>
                </>
              )}
            </Button>
          </div>
        </DialogHeader>

        {/* Search bar inside modal */}
        <div className="px-4 py-2 bg-[#14141f] border-b border-white/5 flex items-center gap-2">
          <Search size={13} className="text-zinc-500" />
          <Input
            placeholder="Search payload fields or values..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-7 bg-transparent border-0 text-xs text-zinc-200 placeholder:text-zinc-500 focus-visible:ring-0 focus-visible:ring-offset-0 px-0"
          />
        </div>

        {/* Code viewer box */}
        <div className="p-4 max-h-[60vh] overflow-y-auto bg-[#0b0b10] font-mono text-xs text-violet-200/90 leading-relaxed scrollbar-thin scrollbar-thumb-white/10">
          <pre className="whitespace-pre-wrap break-all">
            {filteredLines.length > 0 ? (
              filteredLines.join("\n")
            ) : (
              <span className="text-zinc-500 italic">No matching lines found for query "{searchQuery}"</span>
            )}
          </pre>
        </div>
      </DialogContent>
    </Dialog>
  );
}
