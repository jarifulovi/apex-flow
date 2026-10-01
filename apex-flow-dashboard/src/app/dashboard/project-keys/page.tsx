"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/shared/Header";
import { KeyRound, ShieldCheck, Plus, Loader2 } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import {
  getProjectKeys,
  createProjectKey,
  revokeProjectKey,
  type ProjectKey,
  type ProjectKeyCreated,
} from "@/features/project-keys/api";
import {
  ProjectKeyList,
  CreateKeyModal,
} from "@/features/project-keys/components/ProjectKeyList";
import { SDKQuickstart } from "@/features/project-keys/components/SDKQuickstart";

export default function ProjectKeysPage() {
  const { accessToken } = useAuth();
  const [keys, setKeys] = useState<ProjectKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  const loadKeys = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const data = await getProjectKeys(accessToken);
      setKeys(data);
    } catch (err) {
      console.error("Failed to load project keys:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  const handleCreateKey = async (name: string): Promise<ProjectKeyCreated> => {
    if (!accessToken) throw new Error("Not authenticated");
    const created = await createProjectKey(accessToken, name);
    await loadKeys();
    return created;
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!accessToken) return;
    if (!confirm("Are you sure you want to revoke this project key? SDK workers using this key will immediately lose access.")) {
      return;
    }
    try {
      await revokeProjectKey(accessToken, keyId);
      await loadKeys();
    } catch (err) {
      console.error("Failed to revoke key:", err);
    }
  };

  const activeCount = keys.filter((k) => k.status === "active").length;

  return (
    <div className="dashboard-page">
      <Header
        title="Project Keys"
        subtitle="API keys used to authenticate your SDK workers against the backend"
        actions={
          <button
            onClick={() => setModalOpen(true)}
            className="action-btn action-btn--primary"
          >
            <Plus size={15} />
            New Key
          </button>
        }
      />

      <div className="page-content flex flex-col gap-6">
        <div className="info-banner">
          <ShieldCheck size={16} className="text-violet-400 shrink-0" />
          <p className="info-banner-text">
            Keys are shown <strong>once</strong> at creation. Store them securely — ApexFlow only
            stores a SHA-256 hash. Revoke unused keys promptly.
          </p>
        </div>

        <section className="dashboard-section" aria-labelledby="keys-heading">
          <div className="dashboard-section-header">
            <KeyRound size={15} className="section-icon" />
            <h2 id="keys-heading" className="dashboard-section-title">
              Your Keys
              <span className="section-count">{activeCount} active</span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>Loading project keys...</span>
            </div>
          ) : (
            <ProjectKeyList keys={keys} onRevoke={handleRevokeKey} />
          )}
        </section>

        {/* SDK & Worker Quickstart Code Snippets */}
        <section aria-label="SDK Quickstart">
          <SDKQuickstart />
        </section>
      </div>

      <CreateKeyModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreate={handleCreateKey}
      />
    </div>
  );
}
