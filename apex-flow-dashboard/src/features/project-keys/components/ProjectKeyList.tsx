"use client";

import { useState } from "react";
import { KeyRound, Copy, Check, ShieldOff, Plus, Clock, Trash2, X, AlertTriangle } from "lucide-react";
import type { ProjectKey, ProjectKeyCreated } from "@/features/project-keys/api";

const STATUS_CONFIG: Record<
  ProjectKey["status"],
  { label: string; className: string; dot: string }
> = {
  active:  { label: "Active",  className: "status-badge status-badge--completed", dot: "status-dot--completed" },
  revoked: { label: "Revoked", className: "status-badge status-badge--failed",    dot: "status-dot--failed" },
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }
  return (
    <button onClick={handleCopy} className="icon-btn" title="Copy text">
      {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
    </button>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function ProjectKeyList({
  keys,
  onDelete,
}: {
  keys: ProjectKey[];
  onDelete?: (keyId: string) => void;
}) {
  if (keys.length === 0) {
    return (
      <div className="table-empty">
        <KeyRound size={28} className="table-empty-icon" />
        <p className="table-empty-text">No project keys yet</p>
        <p className="table-empty-sub">Create a key to authenticate your SDK workers.</p>
      </div>
    );
  }

  return (
    <div className="key-list">
      {keys.map((key) => {
        const cfg = STATUS_CONFIG[key.status] || STATUS_CONFIG.active;
        return (
          <div key={key.id} className={`key-card ${key.status === "revoked" ? "key-card--revoked" : ""}`}>
            <div className="key-card-left">
              <div className={`table-icon ${key.status === "active" ? "table-icon--violet" : "table-icon--red"}`}>
                {key.status === "active" ? <KeyRound size={14} /> : <ShieldOff size={14} />}
              </div>
              <div>
                <p className="table-name">{key.name}</p>
                <div className="key-prefix-row">
                  <code className="key-prefix">{key.key_prefix}_••••••••••••••••</code>
                  {key.status === "active" && <CopyButton text={`${key.key_prefix}_••••••••••••••••`} />}
                </div>
              </div>
            </div>
            <div className="key-card-right">
              <span className={cfg.className}>
                <span className={`status-dot ${cfg.dot}`} />
                {cfg.label}
              </span>
              <div className="key-meta-col">
                <span className="key-meta-label">Last used</span>
                <span className="key-meta-value">
                  <Clock size={11} className="inline mr-1 opacity-60" />
                  {formatDate(key.last_used_at)}
                </span>
              </div>
              <div className="key-meta-col">
                <span className="key-meta-label">Created</span>
                <span className="key-meta-value">{formatDate(key.created_at)}</span>
              </div>

              {onDelete && (
                <button
                  onClick={() => onDelete(key.id)}
                  className="icon-btn hover:text-red-400 ml-2"
                  title="Delete key"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function CreateKeyModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string) => Promise<ProjectKeyCreated>;
}) {
  const [name, setName] = useState("");
  const [createdKey, setCreatedKey] = useState<ProjectKeyCreated | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await onCreate(name.trim());
      setCreatedKey(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create key");
    } finally {
      setLoading(false);
    }
  }

  function handleCloseModal() {
    setCreatedKey(null);
    setName("");
    setError(null);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-[#161620] border border-white/10 rounded-2xl p-6 shadow-2xl animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-4">
          <h3 className="text-base font-bold text-[#ececee] flex items-center gap-2">
            <KeyRound size={18} className="text-violet-400" />
            {createdKey ? "Project Key Created" : "Create New Project Key"}
          </h3>
          <button onClick={handleCloseModal} className="text-zinc-400 hover:text-white">
            <X size={18} />
          </button>
        </div>

        {createdKey ? (
          <div className="flex flex-col gap-4">
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-200 text-xs flex items-start gap-2">
              <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
              <span>
                Please copy your secret key now. <strong>You will not be able to see it again!</strong>
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-zinc-400 font-medium">Secret Project Key</label>
              <div className="flex items-center gap-2 bg-black/40 border border-white/10 rounded-lg p-3">
                <code className="text-xs font-mono text-violet-300 break-all flex-1">
                  {createdKey.raw_key}
                </code>
                <CopyButton text={createdKey.raw_key} />
              </div>
            </div>

            <button
              onClick={handleCloseModal}
              className="mt-2 w-full py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold rounded-lg transition"
            >
              Done & Saved Key
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-300 text-xs">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-zinc-400 font-medium">Key Name</label>
              <input
                type="text"
                placeholder="e.g. Production Worker Key"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-[#ececee] focus:outline-none focus:border-violet-500/50"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={handleCloseModal}
                className="px-4 py-2 text-xs font-medium text-zinc-400 hover:text-white rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !name.trim()}
                className="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition flex items-center gap-2"
              >
                {loading ? "Creating..." : "Generate Key"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
