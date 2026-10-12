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
  FileCode2,
  HardDrive,
  KeyRound,
  Loader2,
  Lock,
  Package,
  Search,
  ShieldAlert,
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
    };
  }, [isOffloaded, payload]);

  const isEncrypted = useMemo(() => {
    if (payload && typeof payload === "object") {
      return (payload as Record<string, unknown>).$apexflow_encrypted === true;
    }
    return false;
  }, [payload]);

  const encryptedEnvelope = useMemo(() => {
    if (!isEncrypted) return null;
    return payload as {
      $apexflow_encrypted: boolean;
      alg?: string;
      iv: string;
      ciphertext: string;
      key_hint?: string;
    };
  }, [isEncrypted, payload]);

  // Attempt automatic decryption if key is already in sessionStorage
  useEffect(() => {
    if (!isOpen) {
      setDecryptedData(null);
      setDecryptionError(null);
      return;
    }
    if (isEncrypted && encryptedEnvelope) {
      const savedKey = typeof window !== "undefined" ? sessionStorage.getItem("apexflow_e2ee_key") : null;
      if (savedKey) {
        setDecryptionKey(savedKey);
        handleDecryptWithKey(savedKey);
      }
    }
  }, [isOpen, isEncrypted, encryptedEnvelope]);

  const handleDecryptWithKey = async (keyToUse: string) => {
    if (!encryptedEnvelope || !keyToUse.trim()) return;
    try {
      setIsDecrypting(true);
      setDecryptionError(null);
      const res = await decryptPayloadWebCrypto(encryptedEnvelope, keyToUse.trim());
      setDecryptedData(res);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("apexflow_e2ee_key", keyToUse.trim());
      }
    } catch (err: any) {
      setDecryptionError("Incorrect key or corrupted ciphertext.");
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

  const activeDisplayPayload = useMemo(() => {
    if (isEncrypted && decryptedData !== null) {
      return decryptedData;
    }
    return payload;
  }, [isEncrypted, decryptedData, payload]);

  const formattedJson = useMemo(() => {
    if (!activeDisplayPayload || (typeof activeDisplayPayload === "object" && Object.keys(activeDisplayPayload as object).length === 0)) {
      return "{}";
    }
    try {
      return JSON.stringify(activeDisplayPayload, null, mode === "pretty" ? 2 : undefined);
    } catch {
      return String(activeDisplayPayload);
    }
  }, [activeDisplayPayload, mode]);

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
            <div className={`p-1.5 rounded-lg border ${
              isEncrypted
                ? decryptedData !== null
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                  : "bg-amber-500/10 border-amber-500/20 text-amber-400"
                : isOffloaded
                ? "bg-violet-500/10 border-violet-500/20 text-violet-400"
                : "bg-zinc-800 border-white/10 text-zinc-400"
            }`}>
              {isEncrypted ? (
                decryptedData !== null ? <ShieldCheck size={16} /> : <Lock size={16} />
              ) : isOffloaded ? (
                <Package size={16} />
              ) : (
                <FileCode2 size={16} />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <DialogTitle className="text-sm font-semibold text-zinc-100">
                  {title}
                </DialogTitle>
                {isEncrypted && (
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                    decryptedData !== null
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                      : "bg-amber-500/10 border-amber-500/30 text-amber-300"
                  }`}>
                    {decryptedData !== null ? "DECRYPTED (AES-256)" : "ENCRYPTED (AES-GCM)"}
                  </span>
                )}
              </div>
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

        {/* Offloaded Payload Header Banner */}
        {isOffloaded && offloadRef && (
          <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 text-xs text-amber-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <HardDrive size={14} className="text-amber-400" />
              <span>
                Offloaded payload descriptor • Provider:{" "}
                <strong className="text-amber-100 uppercase">{offloadRef.provider || "LOCAL"}</strong> •
                Content: <code>{offloadRef.content_type || "application/octet-stream"}</code>
                {offloadRef.encrypted && (
                  <span className="ml-2 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-mono text-[10px]">
                    ZERO-KNOWLEDGE ENCRYPTED
                  </span>
                )}
              </span>
            </div>
            <span className="text-[11px] text-amber-400/80 font-mono">{formattedSize}</span>
          </div>
        )}

        {/* E2EE Decryption Banner */}
        {isEncrypted && (
          <div className={`px-4 py-2.5 border-b text-xs flex flex-wrap items-center justify-between gap-2 ${
            decryptedData !== null
              ? "bg-emerald-950/20 border-emerald-500/20 text-emerald-200"
              : "bg-amber-950/20 border-amber-500/20 text-amber-200"
          }`}>
            {decryptedData !== null ? (
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Unlock size={14} className="text-emerald-400" />
                  <span>
                    Payload decrypted client-side via <strong>AES-256-GCM</strong>
                    {encryptedEnvelope?.key_hint && (
                      <span className="ml-2 font-mono text-[10px] bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded text-emerald-300">
                        Fingerprint: {encryptedEnvelope.key_hint}
                      </span>
                    )}
                  </span>
                </div>
                <Button
                  onClick={handleForgetSessionKey}
                  variant="ghost"
                  size="sm"
                  className="h-6 text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                >
                  <Lock size={11} className="mr-1" /> Re-lock
                </Button>
              </div>
            ) : (
              <div className="w-full space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldAlert size={15} className="text-amber-400" />
                    <span className="font-medium text-amber-100">
                      Zero-Knowledge Encrypted Payload
                    </span>
                    {encryptedEnvelope?.key_hint && (
                      <span className="font-mono text-[10px] bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded text-amber-300">
                        Fingerprint: {encryptedEnvelope.key_hint}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-zinc-400">
                    Decrypted strictly inside your browser
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <KeyRound size={13} className="absolute left-2.5 top-2 text-zinc-500" />
                    <Input
                      type="password"
                      placeholder="Enter decryption key or passphrase..."
                      value={decryptionKey}
                      onChange={(e) => setDecryptionKey(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleDecryptWithKey(decryptionKey)}
                      className="h-7 pl-8 bg-black/40 border-white/10 text-xs text-zinc-100 placeholder:text-zinc-500 focus-visible:ring-1 focus-visible:ring-amber-500/50"
                    />
                  </div>
                  <Button
                    onClick={() => handleDecryptWithKey(decryptionKey)}
                    disabled={isDecrypting || !decryptionKey.trim()}
                    size="sm"
                    className="h-7 text-xs bg-amber-600 hover:bg-amber-500 text-black font-medium gap-1 px-3"
                  >
                    {isDecrypting ? <Loader2 size={12} className="animate-spin" /> : <Unlock size={12} />}
                    <span>Decrypt</span>
                  </Button>
                </div>

                {decryptionError && (
                  <p className="text-[11px] text-rose-400 font-mono mt-1">
                    ⚠️ {decryptionError}
                  </p>
                )}
              </div>
            )}
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


