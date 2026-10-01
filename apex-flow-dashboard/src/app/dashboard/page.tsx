import type { Metadata } from "next";
import { Header } from "@/components/shared/Header";
import { TrendingUp, Activity } from "lucide-react";
import { DUMMY_STATS, DUMMY_ACTIVITY } from "@/features/dashboard/data";
import {
  StatCards,
  ActivityFeed,
  QuickNav,
} from "@/features/dashboard/components/DashboardWidgets";

export const metadata: Metadata = {
  title: "Dashboard | ApexFlow",
  description: "Monitor your workflows, steps, and orchestration control plane.",
};

export default function DashboardPage() {
  return (
    <div className="dashboard-page">
      <Header
        title="Overview"
        subtitle="Monitor your workflows and orchestration control plane"
      />

      {/* Stats row */}
      <section className="dashboard-stats" aria-label="Key metrics">
        <StatCards stats={DUMMY_STATS} />
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
          <ActivityFeed items={DUMMY_ACTIVITY} />
        </section>
      </div>
    </div>
  );
}
