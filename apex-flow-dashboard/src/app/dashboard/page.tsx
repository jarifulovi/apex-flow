"use client";

import { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/shared/Header";
import { TrendingUp, Activity, Loader2 } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { useProject } from "@/features/projects/context";
import {
  fetchDashboardOverview,
  type DashboardStats,
  type ActivityItem,
} from "@/features/dashboard/api";
import {
  StatCards,
  ActivityFeed,
  QuickNav,
} from "@/features/dashboard/components/DashboardWidgets";

export default function DashboardPage() {
  const { accessToken } = useAuth();
  const { currentProject } = useProject();
  const [data, setData] = useState<{
    stats: DashboardStats;
    activities: ActivityItem[];
  }>({
    stats: {
      totalWorkflows: 0,
      activeSteps: 0,
      completedSteps: 0,
      failedSteps: 0,
      activeKeysCount: 0,
      activeWorkersCount: 0,
      successRatePercent: 0,
      avgDurationSeconds: 0,
    },
    activities: [],
  });
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      const res = await fetchDashboardOverview(accessToken, currentProject?.id);
      setData({
        stats: res.stats,
        activities: res.activities,
      });
    } catch (err) {
      console.error("Failed to load dashboard overview:", err);
    } finally {
      setLoading(false);
    }
  }, [accessToken, currentProject?.id]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  return (
    <div className="dashboard-page">
      <Header
        title="Overview"
        subtitle={`Telemetry & control plane monitoring for ${currentProject?.name || "your project"}`}
      />

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          <Loader2 size={24} className="animate-spin text-violet-400 mr-2" />
          <span>Loading dashboard overview...</span>
        </div>
      ) : (
        <>
          {/* Stats row */}
          <section className="dashboard-stats" aria-label="Key metrics">
            <StatCards stats={data.stats} />
          </section>

          <div className="dashboard-grid">
            {/* Quick nav */}
            <section className="dashboard-section" aria-labelledby="quick-access-heading">
              <div className="dashboard-section-header">
                <TrendingUp size={15} className="section-icon" />
                <h2 id="quick-access-heading" className="dashboard-section-title">
                  Quick Access
                </h2>
              </div>
              <QuickNav />
            </section>

            {/* Recent activity */}
            <section className="dashboard-section" aria-labelledby="activity-heading">
              <div className="dashboard-section-header">
                <Activity size={15} className="section-icon" />
                <h2 id="activity-heading" className="dashboard-section-title">
                  Recent Activity
                </h2>
              </div>
              <ActivityFeed items={data.activities} />
            </section>
          </div>
        </>
      )}
    </div>
  );
}
