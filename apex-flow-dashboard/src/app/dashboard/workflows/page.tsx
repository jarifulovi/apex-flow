"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/shared/Header";
import { GitBranch, Loader2, RefreshCw, Search, Layers } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import {
  getWorkflows,
  getWorkflowStats,
  getWorkflowDefinitions,
  type Workflow,
  type WorkflowDefinitionSummary,
} from "@/features/workflows/api";
import {
  WorkflowTable,
  WorkflowDefinitionTable,
} from "@/features/workflows/components/WorkflowTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/shared/PaginationControls";

const STATUS_FILTERS = ["all", "pending", "running", "completed", "failed", "cancelled"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];
type ViewMode = "definitions" | "runs";
const PAGE_SIZE = 10;

export default function WorkflowsPage() {
  const { accessToken } = useAuth();
  const { currentProject } = useProject();
  const [viewMode, setViewMode] = useState<ViewMode>("definitions");
  const [definitions, setDefinitions] = useState<WorkflowDefinitionSummary[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({
    all: 0, pending: 0, running: 0, completed: 0, failed: 0, cancelled: 0
  });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [currentPage, setCurrentPage] = useState(1);

  const loadDefinitions = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const defs = await getWorkflowDefinitions(accessToken, currentProject?.id, searchQuery);
      setDefinitions(defs);
    } catch (err) {
      console.error("Failed to load workflow definitions:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, currentProject?.id, searchQuery]);

  const loadWorkflowStats = useCallback(async () => {
    if (!accessToken) return;
    try {
      const stats = await getWorkflowStats(accessToken, currentProject?.id);
      setStatusCounts(stats);
    } catch (err) {
      console.error("Failed to load workflow stats:", err);
    }
  }, [accessToken, currentProject?.id]);

  const loadWorkflows = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const offset = (currentPage - 1) * PAGE_SIZE;
      const res = await getWorkflows(
        accessToken,
        currentProject?.id,
        statusFilter,
        PAGE_SIZE,
        offset,
        searchQuery
      );
      setWorkflows(res.data);
      setTotalCount(res.totalCount);
    } catch (err) {
      console.error("Failed to load workflows:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, currentProject?.id, statusFilter, currentPage, searchQuery]);

  useEffect(() => {
    if (viewMode === "definitions") {
      loadDefinitions();
    } else {
      loadWorkflowStats();
      loadWorkflows();
    }
  }, [viewMode, loadDefinitions, loadWorkflowStats, loadWorkflows]);

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (s: StatusFilter) => {
    setStatusFilter(s);
    setCurrentPage(1);
  };

  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    setCurrentPage(1);
  };

  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;

  const handleRefresh = () => {
    if (viewMode === "definitions") {
      loadDefinitions();
    } else {
      loadWorkflowStats();
      loadWorkflows();
    }
  };

  return (
    <div className="dashboard-page">
      <Header
        title="Workflows"
        subtitle={`Workflow definitions catalog and execution history for ${currentProject?.name || "your project"}`}
        actions={
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            className="border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] text-xs gap-1.5"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </Button>
        }
      />

      <div className="page-content space-y-6">
        {/* Top View Mode Switcher & Search */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="filter-tabs w-full sm:w-auto" role="tablist" aria-label="Workflow view mode">
            <button
              role="tab"
              aria-selected={viewMode === "definitions"}
              id="tab-view-definitions"
              className={`filter-tab${viewMode === "definitions" ? " filter-tab--active" : ""}`}
              onClick={() => handleViewModeChange("definitions")}
            >
              <span>Workflow Definitions</span>
            </button>
            <button
              role="tab"
              aria-selected={viewMode === "runs"}
              id="tab-view-runs"
              className={`filter-tab${viewMode === "runs" ? " filter-tab--active" : ""}`}
              onClick={() => handleViewModeChange("runs")}
            >
              <span>All Execution Runs</span>
            </button>
          </div>

          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input
              placeholder={
                viewMode === "definitions"
                  ? "Search workflow definitions..."
                  : "Search by name, ID, or dedup..."
              }
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-9 bg-[#161620] border-white/10 text-zinc-100 text-xs focus:border-violet-500"
            />
          </div>
        </div>

        {viewMode === "runs" && (
          <div className="filter-tabs w-full overflow-x-auto" role="tablist" aria-label="Workflow status filter">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                role="tab"
                aria-selected={statusFilter === s}
                id={`tab-wf-${s}`}
                className={`filter-tab${statusFilter === s ? " filter-tab--active" : ""}`}
                onClick={() => handleStatusFilterChange(s)}
              >
                <span>{s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}</span>
                <span className="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] bg-white/10 text-zinc-300 font-mono font-medium">
                  {statusCounts[s] || 0}
                </span>
              </button>
            ))}
          </div>
        )}

        <section className="dashboard-section" aria-labelledby="workflows-table-heading">
          <div className="dashboard-section-header">
            {viewMode === "definitions" ? (
              <Layers size={15} className="section-icon text-violet-400" />
            ) : (
              <GitBranch size={15} className="section-icon text-violet-400" />
            )}
            <h2 id="workflows-table-heading" className="dashboard-section-title">
              {viewMode === "definitions" ? "Workflow Definitions" : "Workflow Runs"}
              <span className="section-count">
                {viewMode === "definitions" ? definitions.length : totalCount}
              </span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>
                {viewMode === "definitions" ? "Loading workflow definitions..." : "Loading workflows..."}
              </span>
            </div>
          ) : viewMode === "definitions" ? (
            <WorkflowDefinitionTable definitions={definitions} />
          ) : (
            <>
              <WorkflowTable workflows={workflows} />
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
