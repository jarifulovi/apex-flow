"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/shared/Header";
import { GitBranch, Loader2 } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { getWorkflows, type Workflow } from "@/features/workflows/api";
import {
  WorkflowTable,
  WorkflowStatusBar,
} from "@/features/workflows/components/WorkflowTable";

export default function WorkflowsPage() {
  const { accessToken } = useAuth();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);

  const loadWorkflows = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const data = await getWorkflows(accessToken);
      setWorkflows(data);
    } catch (err) {
      console.error("Failed to load workflows:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  return (
    <div className="dashboard-page">
      <Header
        title="Workflows"
        subtitle="All registered workflow execution runs across your system"
      />

      <div className="page-content">
        <WorkflowStatusBar workflows={workflows} />

        <section className="dashboard-section" aria-labelledby="workflows-table-heading">
          <div className="dashboard-section-header">
            <GitBranch size={15} className="section-icon" />
            <h2 id="workflows-table-heading" className="dashboard-section-title">
              All Workflows
              <span className="section-count">{workflows.length}</span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>Loading workflows...</span>
            </div>
          ) : (
            <WorkflowTable workflows={workflows} />
          )}
        </section>
      </div>
    </div>
  );
}
