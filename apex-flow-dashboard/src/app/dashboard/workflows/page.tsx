"use client";

import { Suspense, useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { CalendarClock, GitBranch, Loader2, RefreshCw, Search, Layers } from "lucide-react";
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
import { SchedulesTabContent } from "@/features/schedules/components/SchedulesTabContent";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/shared/PaginationControls";

const STATUS_FILTERS = ["all", "pending", "running", "completed", "failed", "cancelled"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];
type ViewMode = "definitions" | "runs" | "schedules";
const PAGE_SIZE = 10;

function resolveInitialViewMode(tabParam: string | null): ViewMode {
  if (tabParam === "schedules" || tabParam === "runs" || tabParam === "definitions") {
    return tabParam;
  }
  return "definitions";
}

function WorkflowsPageContent() {
  const searchParams = useSearchParams();
  const { accessToken } = useAuth();
  const { currentProject } = useProject();
  const [viewMode, setViewMode] = useState<ViewMode>(() =>
    resolveInitialViewMode(searchParams.get("tab"))
  );
  const [definitions, setDefinitions] = useState<WorkflowDefinitionSummary[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({
    all: 0, pending: 0, running: 0, completed: 0, failed: 0, cancelled: 0
  });
  const [loading, setLoading] = useState(true);
  const [schedulesCount, setSchedulesCount] = useState<number | null>(null);
  const [schedulesLoading, setSchedulesLoading] = useState(false);
  const [scheduleRefreshSignal, setScheduleRefreshSignal] = useState(0);
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
    } else if (viewMode === "runs") {
      loadWorkflowStats();
      loadWorkflows();
    }
  }, [viewMode, loadDefinitions, loadWorkflowStats, loadWorkflows]);

  useEffect(() => {
    if (viewMode !== "schedules" || !accessToken) return;
    getWorkflowDefinitions(accessToken, currentProject?.id)
      .then(setDefinitions)
      .catch((err) => console.error("Failed to load workflow definitions:", err));
  }, [viewMode, accessToken, currentProject?.id]);

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    setCurrentPage(1);
  };

  const handleStatusFilterChange = (s: StatusFilter) => {
    setStatusFilter(s);
    setCurrentPage(1);
  };

  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;
  const knownWorkflowNames = useMemo(
    () => definitions.map((d) => d.workflow_name),
    [definitions]
  );

  const handleRefresh = () => {
    if (viewMode === "definitions") {
      loadDefinitions();
    } else if (viewMode === "runs") {
      loadWorkflowStats();
      loadWorkflows();
    } else {
      setScheduleRefreshSignal((n) => n + 1);
    }
  };

  const isRefreshing = viewMode === "schedules" ? schedulesLoading : loading;
  const searchPlaceholder =
    viewMode === "definitions"
      ? "Search workflows..."
      : viewMode === "schedules"
      ? "Search schedules..."
      : "Search runs by name/id...";

  return (
    <div className="dashboard-page p-6 space-y-6">
      {/* Top View Mode Switcher, Search & Refresh */}
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
          <button
            role="tab"
            aria-selected={viewMode === "schedules"}
            id="tab-view-schedules"
            className={`filter-tab${viewMode === "schedules" ? " filter-tab--active" : ""}`}
            onClick={() => handleViewModeChange("schedules")}
          >
            <CalendarClock size={13} className="inline mr-1.5 opacity-80" />
            <span>Schedules</span>
            {schedulesCount !== null && (
              <span className="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] bg-white/10 text-zinc-300 font-mono font-medium">
                {schedulesCount}
              </span>
            )}
          </button>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input
              type="text"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-9 h-8 bg-[#161620] border-white/10 text-xs text-zinc-200 focus:border-violet-500"
            />
          </div>

          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            className="border-white/10 text-zinc-300 hover:text-white bg-[#1b1b26] text-xs h-8 px-2.5 gap-1.5 shrink-0"
          >
            <RefreshCw size={13} className={isRefreshing ? "animate-spin" : ""} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {viewMode === "schedules" ? (
        <SchedulesTabContent
          accessToken={accessToken}
          projectId={currentProject?.id}
          searchQuery={searchQuery}
          knownWorkflowNames={knownWorkflowNames}
          refreshSignal={scheduleRefreshSignal}
          onCountChange={setSchedulesCount}
          onLoadingChange={setSchedulesLoading}
        />
      ) : (
        <div className="space-y-6">
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
      )}
    </div>
  );
}

export default function WorkflowsPage() {
  return (
    <Suspense
      fallback={
        <div className="dashboard-page p-6 flex items-center justify-center py-12 text-zinc-400">
          <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
          <span>Loading workflows...</span>
        </div>
      }
    >
      <WorkflowsPageContent />
    </Suspense>
  );
}
