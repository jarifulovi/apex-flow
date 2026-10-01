"use client";

import { useState } from "react";
import { KeyRound, Copy, Check, ShieldOff, Shield, Plus, Clock } from "lucide-react";
import type { ProjectKey } from "../data";

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
    <button onClick={handleCopy} className="icon-btn" title="Copy prefix">
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

export function ProjectKeyList({ keys }: { keys: ProjectKey[] }) {
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
        const cfg = STATUS_CONFIG[key.status];
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
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function CreateKeyButton() {
  return (
    <button
      id="create-key-btn"
      className="action-btn action-btn--primary"
      onClick={() => alert("Create key flow — wire to POST /api/v1/project-keys")}
    >
      <Plus size={15} />
      New Key
    </button>
  );
}
