"use client";

import React, { useState, useMemo, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Check,
  Copy,
  Download,
  ExternalLink,
  FileCode2,
  KeyRound,
  Loader2,
  Lock,
  Package,
  Search,
  ShieldCheck,
  Unlock,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

interface PayloadViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  payload: Record<string, unknown> | unknown;
}

/**
 * Check if a MIME type or file extension can be previewed natively in a browser window.
 */
function isPreviewable(contentType?: string, filename?: string): boolean {
  const mime = (contentType || "").toLowerCase();
  const ext = (filename || "").toLowerCase();

  // Text, code, JSON, logs
  if (
    mime.includes("json") ||
    mime.startsWith("text/") ||
    mime.includes("javascript") ||
    mime.includes("xml") ||
    Boolean(ext.match(/\.(json|txt|md|csv|log|yaml|yml|html|xml|js|ts|py|sh)$/))
  ) {
    return true;
  }

  // Images
  if (
    mime.startsWith("image/") ||
    Boolean(ext.match(/\.(png|jpg|jpeg|gif|webp|svg|bmp|ico)$/))
  ) {
    return true;
  }

  // PDFs
  if (mime === "application/pdf" || ext.endsWith(".pdf")) {
    return true;
  }

  return false;
}

/**
 * Fetch offloaded payload blob directly from the configured API control plane.
 */
async function fetchOffloadedBlob(storageKey: string): Promise<Blob> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
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

  const res = await fetch(`${apiUrl}/api/v1/storage/download/${storageKey}${tokenParam}`, { headers });
  if (!res.ok) {
    throw new Error(`Failed to retrieve storage object (${res.status} ${res.statusText})`);
  }
  return await res.blob();
}

/**
 * Browser-side Web Crypto AES-256-GCM decrypt helper
 */
async function decryptPayloadWebCrypto(
  envelope: { iv: string; ciphertext: string },
  passphraseOrKey: string
): Promise<any> {
  const trimmed = passphraseOrKey.trim();
  let rawKey: Uint8Array;

  // 1. 64-char hex key
  if (/^[0-9a-fA-F]{64}$/.test(trimmed)) {
    const match = trimmed.match(/.{1,2}/g);
    rawKey = new Uint8Array(match ? match.map((b) => parseInt(b, 16)) : []);
  } else {
    // 2. Derive 32-byte key using SHA-256
    const enc = new TextEncoder();
    const hashBuffer = await window.crypto.subtle.digest("SHA-256", enc.encode(trimmed));
    rawKey = new Uint8Array(hashBuffer);
  }

  const cryptoKey = await window.crypto.subtle.importKey(
    "raw",
    rawKey as unknown as BufferSource,
    { name: "AES-GCM" },
    false,
    ["decrypt"]
  );

  const iv = Uint8Array.from(atob(envelope.iv), (c) => c.charCodeAt(0));
  const ciphertextWithTag = Uint8Array.from(atob(envelope.ciphertext), (c) => c.charCodeAt(0));

  const decryptedBuffer = await window.crypto.subtle.decrypt(
    { name: "AES-GCM", iv: iv as unknown as BufferSource, tagLength: 128 },
    cryptoKey,
    ciphertextWithTag as unknown as BufferSource
  );

  const decryptedStr = new TextDecoder().decode(decryptedBuffer);
  return JSON.parse(decryptedStr);
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
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // E2EE Decryption state
  const [decryptedData, setDecryptedData] = useState<any>(null);
  const [decryptionKey, setDecryptionKey] = useState("");
  const [decryptionError, setDecryptionError] = useState<string | null>(null);
  const [isDecrypting, setIsDecrypting] = useState(false);

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
      encrypted?: boolean;
      key_hint?: string;
    };
  }, [isOffloaded, payload]);

  const isDirectEncrypted = useMemo(() => {
    if (payload && typeof payload === "object") {
      return (payload as Record<string, unknown>).$apexflow_encrypted === true;
    }
    return false;
  }, [payload]);

  const isOffloadedEncrypted = useMemo(() => {
    return Boolean(isOffloaded && offloadRef?.encrypted === true);
  }, [isOffloaded, offloadRef]);

  const isEncrypted = isDirectEncrypted || isOffloadedEncrypted;

  const directEnvelope = useMemo(() => {
    if (!isDirectEncrypted) return null;
    return payload as {
      $apexflow_encrypted: boolean;
      alg?: string;
      iv: string;
      ciphertext: string;
      key_hint?: string;
    };
  }, [isDirectEncrypted, payload]);

  const canPreview = useMemo(() => {
    if (!isOffloaded) return true;
    return isPreviewable(offloadRef?.content_type, offloadRef?.filename);
  }, [isOffloaded, offloadRef]);

  const formattedSize = useMemo(() => {
    if (!offloadRef?.size_bytes) return null;
    const bytes = offloadRef.size_bytes;
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${(bytes / 1024).toFixed(1)} KB`;
  }, [offloadRef]);

  // Attempt automatic decryption if key is already in sessionStorage
  useEffect(() => {
    if (!isOpen) {
      setDecryptedData(null);
      setDecryptionError(null);
      setActionError(null);
      if (previewBlobUrl) {
        window.URL.revokeObjectURL(previewBlobUrl);
        setPreviewBlobUrl(null);
      }
      return;
    }
    if (isEncrypted) {
      const savedKey = typeof window !== "undefined" ? sessionStorage.getItem("apexflow_e2ee_key") : null;
      if (savedKey) {
        setDecryptionKey(savedKey);
        handleDecryptWithKey(savedKey);
      }
    }
  }, [isOpen, isEncrypted]);

  const handleDecryptWithKey = async (keyToUse: string) => {
    if (!keyToUse.trim()) return;
    try {
      setIsDecrypting(true);
      setDecryptionError(null);
      setActionError(null);

      let envelopeToDecrypt: any = directEnvelope;

      // If offloaded, fetch the encrypted JSON blob from storage
      if (isOffloadedEncrypted && offloadRef) {
        const blob = await fetchOffloadedBlob(offloadRef.key);
        const text = await blob.text();
        envelopeToDecrypt = JSON.parse(text);
      }

      if (!envelopeToDecrypt || !envelopeToDecrypt.iv || !envelopeToDecrypt.ciphertext) {
        throw new Error("Payload envelope is missing IV or ciphertext.");
      }

      const res = await decryptPayloadWebCrypto(envelopeToDecrypt, keyToUse.trim());
      setDecryptedData(res);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("apexflow_e2ee_key", keyToUse.trim());
      }
    } catch (err: any) {
      setDecryptionError(err?.message || "Incorrect decryption key or corrupted ciphertext.");
    } finally {
      setIsDecrypting(false);
    }
  };

  const handleForgetSessionKey = () => {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("apexflow_e2ee_key");
    }
    setDecryptionKey("");
    setDecryptedData(null);
    setDecryptionError(null);
  };

  // Preview in a separate window (avoids page freezing for large payloads)
  const handlePreviewInNewWindow = async () => {
    if (!offloadRef || isPreviewing) return;

    if (isEncrypted && !decryptedData) {
      setActionError("Please enter decryption key to unlock payload before previewing.");
      return;
    }

    // 1. Open new tab synchronously during user click turn so browser popup blockers do not block it
    const newTab = window.open("about:blank", "_blank");
    if (newTab) {
      try {
        newTab.document.title = "Loading preview...";
        newTab.document.body.style.backgroundColor = "#0b0b10";
        newTab.document.body.style.color = "#a1a1aa";
        newTab.document.body.style.fontFamily = "ui-monospace, SFMono-Regular, monospace";
        newTab.document.body.style.display = "flex";
        newTab.document.body.style.alignItems = "center";
        newTab.document.body.style.justifyContent = "center";
        newTab.document.body.style.height = "100vh";
        newTab.document.body.style.margin = "0";
        newTab.document.body.innerHTML = "<p style='letter-spacing:0.05em;'>Loading payload preview...</p>";
      } catch {
        // Safe to ignore if browser restricts about:blank mutation
      }
    }

    try {
      setIsPreviewing(true);
      setActionError(null);

      let blobToOpen: Blob;

      if (isEncrypted) {
        const jsonStr = JSON.stringify(decryptedData, null, 2);
        blobToOpen = new Blob([jsonStr], { type: "application/json" });
      } else {
        const rawBlob = await fetchOffloadedBlob(offloadRef.key);
        const mime = offloadRef.content_type || rawBlob.type || "text/plain";
        blobToOpen = new Blob([rawBlob], { type: mime });
      }

      if (previewBlobUrl) {
        window.URL.revokeObjectURL(previewBlobUrl);
      }
      const blobUrl = window.URL.createObjectURL(blobToOpen);
      setPreviewBlobUrl(blobUrl);

      if (newTab && !newTab.closed) {
        newTab.location.href = blobUrl;
      } else {
        setActionError("Browser blocked opening a new window automatically. Click the link below to open.");
      }
    } catch (err: any) {
      console.error("Preview in new window failed:", err);
      if (newTab && !newTab.closed) {
        newTab.close();
      }
      setActionError(err?.message || "Failed to preview file in new window.");
    } finally {
      setIsPreviewing(false);
    }
  };

  // Download payload to local disk
  const handleDownload = async () => {
    if (!offloadRef || isDownloading) return;
    try {
      setIsDownloading(true);
      setActionError(null);

      let blobToDownload: Blob;
      let filename = offloadRef.filename || offloadRef.key.split("/").pop() || "payload.bin";

      if (isEncrypted) {
        if (!decryptedData) {
          throw new Error("Please enter decryption key to unlock payload before downloading.");
        }
        const jsonStr = JSON.stringify(decryptedData, null, 2);
        blobToDownload = new Blob([jsonStr], { type: "application/json" });
        const baseName = filename.replace(/\.json$/, "");
        filename = `${baseName}_decrypted.json`;
      } else {
        blobToDownload = await fetchOffloadedBlob(offloadRef.key);
      }

      const blobUrl = window.URL.createObjectURL(blobToDownload);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
    } catch (err: any) {
      console.error("Download failed:", err);
      setActionError(err?.message || "Failed to download payload.");
    } finally {
      setIsDownloading(false);
    }
  };

  // Compute text lines only for inline payloads to prevent memory bloat on offloaded data
  const formattedJson = useMemo(() => {
    if (isOffloaded) return "";
    const active = isEncrypted && decryptedData !== null ? decryptedData : payload;
    if (!active || (typeof active === "object" && Object.keys(active as object).length === 0)) {
      return "{}";
    }
    try {
      return JSON.stringify(active, null, mode === "pretty" ? 2 : undefined);
    } catch {
      return String(active);
    }
  }, [isOffloaded, isEncrypted, decryptedData, payload, mode]);

  const filteredLines = useMemo(() => {
    if (isOffloaded || !formattedJson) return [];
    const lines = formattedJson.split("\n");
    if (!searchQuery.trim()) return lines;
    const q = searchQuery.toLowerCase();
    return lines.filter((line) => line.toLowerCase().includes(q));
  }, [isOffloaded, formattedJson, searchQuery]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJson);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy payload to clipboard:", err);
    }
  };

  const lineCount = isOffloaded ? 0 : formattedJson.split("\n").length;
  const byteSize = isOffloaded ? (offloadRef?.size_bytes ?? 0) : new Blob([formattedJson]).size;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl bg-[#12121a] border-white/10 text-zinc-100 shadow-2xl backdrop-blur-xl p-0 gap-0 overflow-hidden rounded-xl sm:max-w-3xl">
        <DialogHeader className="p-3.5 bg-[#181824] border-b border-white/10 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div
              className={`p-1.5 rounded-lg border shrink-0 ${
                isEncrypted
                  ? decryptedData !== null
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                  : isOffloaded
                  ? "bg-violet-500/10 border-violet-500/20 text-violet-400"
                  : "bg-zinc-800 border-white/10 text-zinc-400"
              }`}
            >
              {isEncrypted ? (
                decryptedData !== null ? <ShieldCheck size={15} /> : <Lock size={15} />
              ) : isOffloaded ? (
                <Package size={15} />
              ) : (
                <FileCode2 size={15} />
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <DialogTitle className="text-sm font-semibold text-zinc-100 truncate">
                  {title}
                </DialogTitle>

                {isOffloaded && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-300 shrink-0">
                    {offloadRef?.provider?.toUpperCase() || "STORAGE"}
                  </span>
                )}

                {isEncrypted && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded border flex items-center gap-1 shrink-0 ${
                      decryptedData !== null
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                        : "bg-amber-500/10 border-amber-500/30 text-amber-300"
                    }`}
                  >
                    {decryptedData !== null ? (
                      <>
                        <ShieldCheck size={10} />
                        <span>AES-256</span>
                      </>
                    ) : (
                      <>
                        <Lock size={10} />
                        <span>ENCRYPTED</span>
                      </>
                    )}
                  </span>
                )}
              </div>

              <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                {isOffloaded
                  ? `${formattedSize || `${byteSize} B`} • Offloaded Payload`
                  : `${lineCount} ${lineCount === 1 ? "line" : "lines"} • ${byteSize} B`}
              </p>
            </div>
          </div>

          {/* Action buttons in header for inline small payloads */}
          {!isOffloaded && (
            <div className="flex items-center gap-1.5 mr-6 shrink-0">
              <div className="flex items-center bg-[#0d0d14] rounded-lg p-0.5 border border-white/10 shrink-0">
                <button
                  onClick={() => setMode("pretty")}
                  className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors ${
                    mode === "pretty"
                      ? "bg-violet-600 text-white shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Pretty
                </button>
                <button
                  onClick={() => setMode("raw")}
                  className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors ${
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
                className="h-7 w-7 p-0 bg-[#1b1b26] border-white/10 text-zinc-200 hover:text-white shrink-0 flex items-center justify-center"
                title={copied ? "Copied to clipboard" : "Copy to clipboard"}
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
              </Button>
            </div>
          )}
        </DialogHeader>

        {/* Minimal inline unlock strip (shown when encrypted & locked) */}
        {isEncrypted && decryptedData === null && (
          <div className="px-4 py-2 bg-amber-500/[0.04] border-b border-amber-500/20 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-amber-300/90 shrink-0">
              <KeyRound size={13} className="text-amber-400" />
              <span className="font-medium text-amber-200">Decryption Key</span>
            </div>

            <div className="flex items-center gap-2 flex-1 max-w-sm ml-auto">
              <Input
                type="password"
                placeholder="Enter passphrase..."
                value={decryptionKey}
                onChange={(e) => setDecryptionKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleDecryptWithKey(decryptionKey)}
                className="h-7 bg-black/40 border-white/10 text-xs text-zinc-100 placeholder:text-zinc-500 focus-visible:ring-1 focus-visible:ring-amber-500/50"
              />
              <Button
                onClick={() => handleDecryptWithKey(decryptionKey)}
                disabled={isDecrypting || !decryptionKey.trim()}
                size="sm"
                className="h-7 text-xs bg-amber-500 hover:bg-amber-400 text-black font-medium gap-1 px-3 shrink-0"
              >
                {isDecrypting ? <Loader2 size={12} className="animate-spin" /> : <Unlock size={12} />}
                <span>Unlock</span>
              </Button>
            </div>

            {decryptionError && (
              <span className="text-[11px] text-rose-400 font-mono shrink-0">⚠️ {decryptionError}</span>
            )}
          </div>
        )}

        {/* View Mode 1: Offloaded Payload (No in-modal DOM dump; Two Options: Preview in New Window & Download) */}
        {isOffloaded ? (
          <div className="p-5 space-y-4 bg-[#0b0b10]">
            <div className="p-4 rounded-xl bg-[#14141f] border border-white/5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Package size={15} className="text-violet-400 shrink-0" />
                  <span className="text-sm font-semibold text-zinc-100 font-mono truncate">
                    {offloadRef?.filename || offloadRef?.key.split("/").pop() || "payload.bin"}
                  </span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-300 shrink-0">
                  {offloadRef?.provider?.toUpperCase() || "STORAGE"}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs border-t border-white/5 font-mono">
                <div>
                  <p className="text-[10px] uppercase text-zinc-500">File Size</p>
                  <p className="text-zinc-200 mt-0.5">{formattedSize || "—"}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-zinc-500">Content Type</p>
                  <p className="text-zinc-200 mt-0.5 truncate" title={offloadRef?.content_type}>
                    {offloadRef?.content_type || "application/octet-stream"}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-zinc-500">Security</p>
                  <p className="mt-0.5 flex items-center gap-1">
                    {isEncrypted ? (
                      decryptedData !== null ? (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <ShieldCheck size={12} /> Decrypted
                        </span>
                      ) : (
                        <span className="text-amber-400 flex items-center gap-1">
                          <Lock size={12} /> AES-256
                        </span>
                      )
                    ) : (
                      <span className="text-zinc-400">Plaintext</span>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-zinc-500">Storage Key</p>
                  <p className="text-zinc-400 mt-0.5 truncate" title={offloadRef?.key}>
                    {offloadRef?.key}
                  </p>
                </div>
              </div>
            </div>

            {/* Status notice */}
            <div className="p-3 rounded-lg bg-zinc-900/60 border border-white/5 text-xs text-zinc-400">
              {canPreview
                ? "This large payload is stored in durable object storage. You can preview it in a dedicated browser tab or download it to your local machine."
                : "This binary file format cannot be rendered as text in the browser. You can download it directly to inspect with local tools."}
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              {canPreview && (!isEncrypted || decryptedData !== null) && (
                <Button
                  onClick={handlePreviewInNewWindow}
                  disabled={isPreviewing}
                  className="bg-violet-600 hover:bg-violet-500 text-white text-xs h-8 px-3.5 gap-1.5 font-medium shadow-sm"
                >
                  {isPreviewing ? <Loader2 size={13} className="animate-spin" /> : <ExternalLink size={13} />}
                  <span>Preview in New Window</span>
                </Button>
              )}

              {(!isEncrypted || decryptedData !== null) && (
                <Button
                  onClick={handleDownload}
                  disabled={isDownloading}
                  variant="outline"
                  className="bg-[#1b1b26] hover:bg-[#232332] border-white/10 text-zinc-200 hover:text-white text-xs h-8 px-3.5 gap-1.5 font-medium"
                >
                  {isDownloading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                  <span>{isEncrypted ? "Download Decrypted JSON" : "Download File"}</span>
                </Button>
              )}

              {isEncrypted && decryptedData === null && (
                <span className="text-xs text-amber-300/80 font-mono flex items-center gap-1.5">
                  <Lock size={12} /> Enter decryption key above to unlock preview and download.
                </span>
              )}
            </div>

            {/* Error banner with fallback manual link if blocked */}
            {actionError && (
              <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300 font-mono space-y-2">
                <div>⚠️ {actionError}</div>
                {previewBlobUrl && (
                  <div>
                    <a
                      href={previewBlobUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-violet-300 hover:text-white underline"
                    >
                      <ExternalLink size={12} />
                      <span>Click here to open preview tab manually</span>
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          /* View Mode 2: Inline Small Payload (< 250KB) */
          <>
            <div className="px-4 py-1.5 bg-[#14141f] border-b border-white/5 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-1">
                <Search size={13} className="text-zinc-500 shrink-0" />
                <Input
                  placeholder="Search fields or values..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-6 bg-transparent border-0 text-xs text-zinc-200 placeholder:text-zinc-500 focus-visible:ring-0 focus-visible:ring-offset-0 px-0"
                />
              </div>

              {isEncrypted && decryptedData !== null && (
                <button
                  onClick={handleForgetSessionKey}
                  className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1 transition-colors px-2 py-0.5 rounded hover:bg-white/5 font-medium shrink-0"
                  title="Lock payload and clear key from session"
                >
                  <Lock size={11} className="text-zinc-500" />
                  <span>Lock</span>
                </button>
              )}
            </div>

            <div className="p-4 max-h-[60vh] overflow-y-auto bg-[#0b0b10] font-mono text-xs text-violet-200/90 leading-relaxed scrollbar-thin scrollbar-thumb-white/10">
              <pre className="whitespace-pre-wrap break-all">
                {filteredLines.length > 0 ? (
                  filteredLines.join("\n")
                ) : (
                  <span className="text-zinc-500 italic">No matching lines found for query "{searchQuery}"</span>
                )}
              </pre>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
