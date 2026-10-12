"use client";

import React, { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Check, Copy, Download, FileCode2, HardDrive, Loader2, Package, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

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
  const [isDownloading, setIsDownloading] = useState(false);

  const isOffloaded = useMemo(() => {
    return Boolean(
      payload &&
      typeof payload === "object" &&
      (payload as Record<string, unknown>).$apexflow_ref === true
    );
  }, [payload]);

  const offloadRef = useMemo(() => {
    if (!isOffloaded) return null;
    return payload as {
      key: string;
      size_bytes?: number;
      content_type?: string;
      filename?: string;
      provider?: string;
    };
  }, [isOffloaded, payload]);

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

  const handleDownload = async () => {
    if (!offloadRef || isDownloading) return;
    try {
      setIsDownloading(true);
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      const headers: Record<string, string> = {};
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      const tokenParam = session?.access_token
        ? `?token=${encodeURIComponent(session.access_token)}`
        : "";
      const downloadUrl = `${backendUrl}/api/v1/storage/download/${offloadRef.key}${tokenParam}`;

      const res = await fetch(downloadUrl, { headers });
      if (!res.ok) {
        throw new Error(`Download failed with status ${res.status}`);
      }

      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = offloadRef.filename || offloadRef.key.split("/").pop() || "payload.json";
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
    } catch (err) {
      console.error("Failed to download payload:", err);
    } finally {
      setIsDownloading(false);
    }
  };

  const lineCount = formattedJson.split("\n").length;
  const byteSize = new Blob([formattedJson]).size;

  const formattedSize = useMemo(() => {
    if (!offloadRef?.size_bytes) return null;
    const bytes = offloadRef.size_bytes;
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
  }, [offloadRef]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-[#12121a] border-white/10 text-zinc-100 shadow-2xl backdrop-blur-xl p-0 gap-0 overflow-hidden rounded-xl sm:max-w-2xl">
        <DialogHeader className="p-4 bg-[#181824] border-b border-white/10 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-400">
              {isOffloaded ? <Package size={16} /> : <FileCode2 size={16} />}
            </div>
            <div>
              <DialogTitle className="text-sm font-semibold text-zinc-100">
                {title}
              </DialogTitle>
              <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                {isOffloaded
                  ? `📦 Offloaded Storage (${formattedSize || byteSize + " B"})`
                  : `${lineCount} ${lineCount === 1 ? "line" : "lines"} • ${byteSize} bytes`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 mr-6">
            {isOffloaded && (
              <Button
                onClick={handleDownload}
                disabled={isDownloading}
                variant="outline"
                size="sm"
                className="h-7 text-xs bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20 gap-1.5"
              >
                {isDownloading ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Download size={12} />
                )}
                <span>{isDownloading ? "Downloading..." : "Download Payload"}</span>
              </Button>
            )}

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

        {isOffloaded && offloadRef && (
          <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 text-xs text-amber-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HardDrive size={14} className="text-amber-400" />
              <span>
                Offloaded payload descriptor • Provider:{" "}
                <strong className="text-amber-100 uppercase">{offloadRef.provider || "LOCAL"}</strong> •
                Content: <code>{offloadRef.content_type || "application/octet-stream"}</code>
              </span>
            </div>
            <span className="text-[11px] text-amber-400/80 font-mono">{formattedSize}</span>
          </div>
        )}

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

