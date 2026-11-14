"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { Header } from "@/components/shared/Header";
import {
  GitBranch,
  Loader2,
  RefreshCw,
  Search,
  TrendingUp,
  Activity,
  Timer,
} from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import {
  getWorkflows,
  getWorkflowStats,
  getWorkflowDefinitions,
  type Workflow,
  type WorkflowDefinitionSummary,
} from "@/features/workflows/api";
import { WorkflowTable } from "@/features/workflows/components/WorkflowTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/shared/PaginationControls";

const STATUS_FILTERS = ["all", "pending", "running", "completed", "failed", "cancelled"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];
const PAGE_SIZE = 10;

function formatAvgDuration(seconds?: number | null): string {
  if (seconds === undefined || seconds === null) return "—";
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs}s`;
}

export default function WorkflowDefinitionDetailPage() {
  const params = useParams<{ name: string }>();
  const workflowName = params?.name ? decodeURIComponent(params.name) : "";

  const { accessToken } = useAuth();
  const { currentProject } = useProject();

  const [summary, setSummary] = useState<WorkflowDefinitionSummary | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({
    all: 0, pending: 0, running: 0, completed: 0, failed: 0, cancelled: 0,
  });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [currentPage, setCurrentPage] = useState(1);

  const loadAnalytics = useCallback(async () => {
    if (!accessToken || !workflowName) return;
    try {
      const [defs, stats] = await Promise.all([
        getWorkflowDefinitions(accessToken, currentProject?.id, workflowName),
        getWorkflowStats(accessToken, currentProject?.id, workflowName),
      ]);
      const matched = defs.find((d) => d.workflow_name === workflowName) || null;
      setSummary(matched);
      setStatusCounts(stats);
    } catch (err) {
      console.error("Failed to load workflow analytics:", err);
    }
  }, [accessToken, currentProject?.id, workflowName]);

  const loadRuns = useCallback(async () => {
    if (!accessToken || !workflowName) return;
    try {
      setLoading(true);
      const offset = (currentPage - 1) * PAGE_SIZE;
      const res = await getWorkflows(
        accessToken,
        currentProject?.id,
        statusFilter,
        PAGE_SIZE,
        offset,
        searchQuery,
        undefined,
        workflowName
      );
      setWorkflows(res.data);
      setTotalCount(res.totalCount);
    } catch (err) {
      console.error("Failed to load workflow runs:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, currentProject?.id, workflowName, statusFilter, currentPage, searchQuery]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const handleStatusFilterChange = (s: StatusFilter) => {
    setStatusFilter(s);
    setCurrentPage(1);
  };

  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    loadAnalytics();
    loadRuns();
  };

  const totalPages = Math.ceil(totalCount / PAGE_SIZE) || 1;

  const statCards = [
    {
      id: "def-stat-total",
      label: "Total Runs",
      value: (summary?.total_runs ?? statusCounts.all ?? 0).toLocaleString(),
      icon: GitBranch,
      color: "violet",
      hint: "All recorded executions",
    },
    {
      id: "def-stat-success-rate",
      label: "Success Rate",
      value: `${(summary?.success_rate ?? 0).toFixed(1)}%`,
      icon: TrendingUp,
      color: "emerald",
      hint: `${summary?.failed_runs ?? statusCounts.failed ?? 0} failed runs`,
    },
    {
      id: "def-stat-active",
      label: "Active Runs",
      value: (summary?.active_runs ?? ((statusCounts.pending || 0) + (statusCounts.running || 0))).toLocaleString(),
      icon: Activity,
      color: "cyan",
      hint: "Pending or running",
    },
    {
      id: "def-stat-duration",
      label: "Avg Duration",
      value: formatAvgDuration(summary?.avg_duration_seconds),
      icon: Timer,
      color: "amber",
      hint: "Completed execution avg",
    },
  ];

  return (
    <div className="dashboard-page">
      <Header
        title={workflowName || "Workflow Analytics"}
        subtitle={`Workflow identity analytics and execution history for ${currentProject?.name || "your project"}`}
        backUrl="/dashboard/workflows"
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
        {/* Analytics KPI Banner */}
        <section className="dashboard-stats" aria-label="Workflow analytics">
          {statCards.map(({ id, label, value, icon: Icon, color, hint }) => (
            <div key={id} id={id} className={`stat-card stat-card--${color}`}>
              <div className="stat-card-header">
                <span className="stat-card-label">{label}</span>
                <div className={`stat-card-icon stat-card-icon--${color}`}>
                  <Icon size={14} />
                </div>
              </div>
              <p className="stat-card-value">{value}</p>
              <p className="stat-card-hint">{hint}</p>
            </div>
          ))}
        </section>

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="filter-tabs w-full sm:w-auto overflow-x-auto" role="tablist" aria-label="Workflow status filter">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                role="tab"
                aria-selected={statusFilter === s}
                id={`tab-def-wf-${s}`}
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

          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <Input
              placeholder="Search by run ID or dedup..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-9 bg-[#161620] border-white/10 text-zinc-100 text-xs focus:border-violet-500"
            />
          </div>
        </div>

        {/* Runs Table */}
        <section className="dashboard-section" aria-labelledby="def-runs-table-heading">
          <div className="dashboard-section-header">
            <GitBranch size={15} className="section-icon text-violet-400" />
            <h2 id="def-runs-table-heading" className="dashboard-section-title">
              Execution Runs
              <span className="section-count">{totalCount}</span>
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-zinc-400">
              <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
              <span>Loading execution runs...</span>
            </div>
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

