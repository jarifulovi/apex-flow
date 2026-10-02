"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/shared/Header";
import { Cpu, Loader2, RefreshCw } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import { getWorkers, type Worker } from "@/features/workers/api";
import { WorkerList } from "@/features/workers/components/WorkerList";
import { Button } from "@/components/ui/button";

export default function WorkersPage() {
  const { accessToken } = useAuth();
  const { currentProject } = useProject();
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);

  const loadWorkers = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const data = await getWorkers(accessToken, currentProject?.id);
      setWorkers(data);
    } catch (err) {
      console.error("Failed to load workers:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, currentProject?.id]);

  useEffect(() => {
    loadWorkers();
  }, [loadWorkers]);

  return (
    <div className="dashboard-page">
      <Header
        title="Execution Workers"
        subtitle="Monitor connected python SDK workers polling and executing step queues"
        actions={
          <Button
            onClick={loadWorkers}
            variant="outline"
            size="sm"
            className="border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] text-xs gap-1.5"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </Button>
        }
      />

      <div className="page-content">
        <section className="dashboard-section" aria-labelledby="workers-heading">
          <div className="dashboard-section-header">
            <Cpu size={15} className="section-icon" />
            <h2 id="workers-heading" className="dashboard-section-title">
              Active Workers
              <span className="section-count">{workers.length}</span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>Loading execution workers...</span>
            </div>
          ) : (
            <WorkerList workers={workers} />
          )}
        </section>
      </div>
    </div>
  );
}
