"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { Header } from "@/components/shared/Header";
import { Footprints, Loader2, RefreshCw, Search } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import { getSteps, type WorkflowStep } from "@/features/steps/api";
import { StepsTable } from "@/features/steps/components/StepsTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/shared/PaginationControls";

const ALL_STATUSES = ["all", "queued", "running", "success", "failed", "cancelled"] as const;
type FilterStatus = (typeof ALL_STATUSES)[number];
const PAGE_SIZE = 10;

export default function StepsPage() {
  const { accessToken } = useAuth();
  const { currentProject } = useProject();
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  const loadSteps = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const data = await getSteps(accessToken, currentProject?.id, filter === "all" ? undefined : filter);
      setSteps(data);
    } catch (err) {
      console.error("Failed to load steps:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, currentProject?.id, filter]);

  useEffect(() => {
    loadSteps();
  }, [loadSteps]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filter, currentProject?.id]);

  const filteredSteps = useMemo(() => {
    return steps.filter((step) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        step.step_name.toLowerCase().includes(q) ||
        step.id.toLowerCase().includes(q) ||
        (step.workflow_run_id && step.workflow_run_id.toLowerCase().includes(q));
      return matchesSearch;
    });
  }, [steps, searchQuery]);

  const totalPages = Math.ceil(filteredSteps.length / PAGE_SIZE) || 1;
  const paginatedSteps = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredSteps.slice(start, start + PAGE_SIZE);
  }, [filteredSteps, currentPage]);

  return (
    <div className="dashboard-page">
      <Header
        title="Execution Step Queues"
        subtitle={`Track execution status, retries, and durations for ${currentProject?.name || "your project"}`}
        actions={
          <Button
            onClick={loadSteps}
            variant="outline"
            size="sm"
            className="border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] text-[#e4e4e7] text-xs gap-1.5 hover:bg-[#252536]"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </Button>
        }
      />

      <div className="page-content space-y-6">
        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="filter-tabs w-full sm:w-auto" role="tablist" aria-label="Step status filter">
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

          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input
              placeholder="Search steps or run ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-[#161620] border-white/10 text-zinc-100 text-xs focus:border-violet-500"
            />
          </div>
        </div>

        <section className="dashboard-section" aria-labelledby="steps-table-heading">
          <div className="dashboard-section-header">
            <Footprints size={15} className="section-icon text-violet-400" />
            <h2 id="steps-table-heading" className="dashboard-section-title">
              Execution Steps
              <span className="section-count">{filteredSteps.length}</span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>Loading steps...</span>
            </div>
          ) : (
            <>
              <StepsTable steps={paginatedSteps} />
              <PaginationControls
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                pageSize={PAGE_SIZE}
                totalItems={filteredSteps.length}
                loading={loading}
              />
            </>
          )}
        </section>
      </div>
    </div>
  );
}
