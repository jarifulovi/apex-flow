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

  const activeKeyHint = useMemo(() => {
    if (directEnvelope?.key_hint) return directEnvelope.key_hint;
    if (offloadRef?.key_hint) return offloadRef.key_hint;
    return null;
  }, [directEnvelope, offloadRef]);

  // Attempt automatic decryption if key is already in sessionStorage
  useEffect(() => {
    if (!isOpen) {
      setDecryptedData(null);
      setDecryptionError(null);
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

      let envelopeToDecrypt: any = directEnvelope;

      // If offloaded, fetch the encrypted JSON blob from durable storage first
      if (isOffloadedEncrypted && offloadRef) {
        const primaryUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const fallbackUrl = "https://apex-flow-backend-kt5d.onrender.com";
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

        let res = await fetch(`${primaryUrl}/api/v1/storage/download/${offloadRef.key}${tokenParam}`, { headers });
        if (!res.ok && res.status === 404 && primaryUrl.includes("localhost")) {
          // If running localhost dashboard but workflow was offloaded to deployed Render S3 storage
          res = await fetch(`${fallbackUrl}/api/v1/storage/download/${offloadRef.key}${tokenParam}`, { headers });
        }

        if (!res.ok) {
          throw new Error(`Failed to download cloud payload (${res.status} ${res.statusText})`);
        }
        envelopeToDecrypt = await res.json();
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
      setDecryptionError(err?.message || "Incorrect key or corrupted ciphertext.");
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
      const primaryUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const fallbackUrl = "https://apex-flow-backend-kt5d.onrender.com";
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

      let res = await fetch(`${primaryUrl}/api/v1/storage/download/${offloadRef.key}${tokenParam}`, { headers });
      if (!res.ok && res.status === 404 && primaryUrl.includes("localhost")) {
        res = await fetch(`${fallbackUrl}/api/v1/storage/download/${offloadRef.key}${tokenParam}`, { headers });
      }

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

  const handleDownloadDecrypted = () => {
    if (!decryptedData) return;
    try {
      const jsonStr = JSON.stringify(decryptedData, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      const baseName = (offloadRef?.filename || "payload").replace(/\.json$/, "");
      link.download = `${baseName}_decrypted.json`;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(blobUrl);
      document.body.removeChild(link);
    } catch (err) {
      console.error("Failed to download decrypted payload:", err);
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
        <DialogHeader className="p-3.5 bg-[#181824] border-b border-white/10 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2.5">
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
                decryptedData !== null ? <ShieldCheck size={15} /> : <Lock size={15} />
              ) : isOffloaded ? (
                <Package size={15} />
              ) : (
                <FileCode2 size={15} />
              )}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <DialogTitle className="text-sm font-semibold text-zinc-100">
                  {title}
                </DialogTitle>

                {isOffloaded && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-300">
                    {offloadRef?.provider?.toUpperCase() || "STORAGE"} • {formattedSize || `${byteSize} B`}
                  </span>
                )}

                {isEncrypted && (
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border flex items-center gap-1 ${
                    decryptedData !== null
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                      : "bg-amber-500/10 border-amber-500/30 text-amber-300"
                  }`}>
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

                {activeKeyHint && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-zinc-400">
                    #{activeKeyHint}
                  </span>
                )}
              </div>

              <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                {lineCount} {lineCount === 1 ? "line" : "lines"} • {byteSize} bytes
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 mr-6">
            {/* Download Action */}
            {decryptedData !== null ? (
              <Button
                onClick={handleDownloadDecrypted}
                variant="outline"
                size="sm"
                className="h-7 text-xs bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20 gap-1.5"
                title="Download decrypted JSON"
              >
                <Download size={12} />
                <span>Decrypted JSON</span>
              </Button>
            ) : isOffloaded ? (
              <Button
                onClick={handleDownload}
                disabled={isDownloading}
                variant="outline"
                size="sm"
                className="h-7 text-xs bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20 gap-1.5"
                title="Download raw file from storage"
              >
                {isDownloading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                <span>Download</span>
              </Button>
            ) : null}

            {/* Pretty / Raw Switch */}
            <div className="flex items-center bg-[#0d0d14] rounded-lg p-0.5 border border-white/10">
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

            {/* Copy Button */}
            <Button
              onClick={handleCopy}
              variant="outline"
              size="sm"
              className="h-7 text-xs bg-[#1b1b26] border-white/10 text-zinc-200 hover:text-white gap-1 px-2.5"
            >
              {copied ? (
                <>
                  <Check size={12} className="text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
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

        {/* Minimal inline unlock strip (only shown when encrypted & locked) */}
        {isEncrypted && decryptedData === null && (
          <div className="px-4 py-2 bg-amber-500/[0.04] border-b border-amber-500/20 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-amber-300/90 shrink-0">
              <KeyRound size={13} className="text-amber-400" />
              <span className="font-medium text-amber-200">Decryption Key</span>
              {activeKeyHint && (
                <span className="font-mono text-[10px] text-amber-400/70">({activeKeyHint})</span>
              )}
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

        {/* Compact search bar & lock toggle */}
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


