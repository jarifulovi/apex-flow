"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/shared/Header";
import { Footprints, Loader2, RefreshCw, Search } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import { getSteps, getStepStats, type WorkflowStep } from "@/features/steps/api";
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
  const [totalCount, setTotalCount] = useState(0);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({
    all: 0, queued: 0, running: 0, success: 0, failed: 0, cancelled: 0
  });
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  const loadStepStats = useCallback(async () => {
    if (!accessToken) return;
    try {
      const stats = await getStepStats(accessToken, currentProject?.id);
      setStatusCounts(stats);
    } catch (err) {
      console.error("Failed to load step stats:", err);
    }
  }, [accessToken, currentProject?.id]);

  const loadSteps = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const offset = (currentPage - 1) * PAGE_SIZE;
      const res = await getSteps(
        accessToken,
        currentProject?.id,
        filter === "all" ? undefined : filter,
        PAGE_SIZE,
        offset,
        searchQuery
      );
      setSteps(res.data);
      setTotalCount(res.totalCount);
    } catch (err) {
      console.error("Failed to load steps:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, currentProject?.id, filter, currentPage, searchQuery]);

  useEffect(() => {
    loadStepStats();
  }, [loadStepStats]);

  useEffect(() => {
    loadSteps();
  }, [loadSteps]);

  const handleFilterChange = (s: FilterStatus) => {
    setFilter(s);
    setCurrentPage(1);
  };

  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    setCurrentPage(1);
  };

  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;

  const handleRefresh = () => {
    loadStepStats();
    loadSteps();
  };

  return (
    <div className="dashboard-page">
      <Header
        title="Execution Step Queues"
        subtitle={`Track execution status, retries, and durations for ${currentProject?.name || "your project"}`}
        actions={
          <Button
            onClick={handleRefresh}
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
          <div className="filter-tabs w-full sm:w-auto overflow-x-auto" role="tablist" aria-label="Step status filter">
            {ALL_STATUSES.map((s) => (
              <button
                key={s}
                role="tab"
                aria-selected={filter === s}
                id={`tab-steps-${s}`}
                className={`filter-tab${filter === s ? " filter-tab--active" : ""}`}
                onClick={() => handleFilterChange(s)}
              >
                <span>{s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}</span>
                <span className="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] bg-white/10 text-zinc-300 font-mono font-medium">
                  {statusCounts[s] || 0}
                </span>
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input
              placeholder="Search steps or run ID..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-9 bg-[#161620] border-white/10 text-zinc-100 text-xs focus:border-violet-500"
            />
          </div>
        </div>

        <section className="dashboard-section" aria-labelledby="steps-table-heading">
          <div className="dashboard-section-header">
            <Footprints size={15} className="section-icon text-violet-400" />
            <h2 id="steps-table-heading" className="dashboard-section-title">
              Execution Steps
              <span className="section-count">{totalCount}</span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>Loading steps...</span>
            </div>
          ) : (
            <>
              <StepsTable steps={steps} />
              <PaginationControls
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                pageSize={PAGE_SIZE}
                totalItems={totalCount}
                loading={loading}
              />
            </>
          )}
        </section>
      </div>
    </div>
  );
}
