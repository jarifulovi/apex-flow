"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/shared/Header";
import { Footprints, Loader2 } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { getSteps, type WorkflowStep } from "@/features/steps/api";
import { StepsTable } from "@/features/steps/components/StepsTable";

const ALL_STATUSES = ["all", "queued", "running", "success", "failed"] as const;
type FilterStatus = (typeof ALL_STATUSES)[number];

export default function StepsPage() {
  const { accessToken } = useAuth();
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [loading, setLoading] = useState(true);

  const loadSteps = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const data = await getSteps(accessToken, filter);
      setSteps(data);
    } catch (err) {
      console.error("Failed to load steps:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, filter]);

  useEffect(() => {
    loadSteps();
  }, [loadSteps]);

  return (
    <div className="dashboard-page">
      <Header
        title="Steps"
        subtitle="Track execution, attempts and errors across all workflow steps"
      />

      <div className="page-content">
        {/* Filter tabs */}
        <div className="filter-tabs" role="tablist" aria-label="Step status filter">
          {ALL_STATUSES.map((s) => (
            <button
              key={s}
              role="tab"
              aria-selected={filter === s}
              id={`tab-steps-${s}`}
              className={`filter-tab${filter === s ? " filter-tab--active" : ""}`}
              onClick={() => setFilter(s)}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        <section className="dashboard-section" aria-labelledby="steps-table-heading">
          <div className="dashboard-section-header">
            <Footprints size={15} className="section-icon" />
            <h2 id="steps-table-heading" className="dashboard-section-title">
              Execution Steps
              <span className="section-count">{steps.length}</span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>Loading steps...</span>
            </div>
          ) : (
            <StepsTable steps={steps} />
          )}
        </section>
      </div>
    </div>
  );
}
