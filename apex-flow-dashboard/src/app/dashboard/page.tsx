import type { Metadata } from "next";
import { Header } from "@/components/shared/Header";
import {
  GitBranch,
  Footprints,
  KeyRound,
  CheckCircle2,
  Clock,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Dashboard | ApexFlow",
};

const STAT_CARDS = [
  {
    id: "stat-workflows",
    label: "Total Workflows",
    value: "—",
    icon: GitBranch,
    color: "violet",
    hint: "Registered workflows",
  },
  {
    id: "stat-steps-pending",
    label: "Pending Steps",
    value: "—",
    icon: Clock,
    color: "amber",
    hint: "Awaiting a worker",
  },
  {
    id: "stat-steps-done",
    label: "Completed Steps",
    value: "—",
    icon: CheckCircle2,
    color: "emerald",
    hint: "Successfully processed",
  },
  {
    id: "stat-steps-failed",
    label: "Failed Steps",
    value: "—",
    icon: AlertTriangle,
    color: "red",
    hint: "Require attention",
  },
];

const QUICK_LINKS = [
  {
    id: "quick-workflows",
    href: "/dashboard/workflows",
    label: "Workflows",
    desc: "Browse and manage all registered workflows",
    icon: GitBranch,
  },
  {
    id: "quick-steps",
    href: "/dashboard/steps",
    label: "Steps",
    desc: "Monitor pending, running and completed steps",
    icon: Footprints,
  },
  {
    id: "quick-keys",
    href: "/dashboard/project-keys",
    label: "Project Keys",
    desc: "Manage API keys used by your workers and SDKs",
    icon: KeyRound,
  },
];

export default function DashboardPage() {
  return (
    <div className="dashboard-page">
      <Header
        title="Overview"
        subtitle="Monitor your workflows and orchestration control plane"
      />

      {/* Stats row */}
      <section className="dashboard-stats" aria-label="Key metrics">
        {STAT_CARDS.map(({ id, label, value, icon: Icon, color, hint }) => (
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

      {/* Quick nav */}
      <section className="dashboard-section" aria-labelledby="quick-access-heading">
        <div className="dashboard-section-header">
          <TrendingUp size={16} className="text-violet-400" />
          <h2 id="quick-access-heading" className="dashboard-section-title">
            Quick Access
          </h2>
        </div>
        <div className="quick-links">
          {QUICK_LINKS.map(({ id, href, label, desc, icon: Icon }) => (
            <a key={id} id={id} href={href} className="quick-link-card">
              <div className="quick-link-icon">
                <Icon size={18} />
              </div>
              <div>
                <p className="quick-link-label">{label}</p>
                <p className="quick-link-desc">{desc}</p>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Placeholder activity */}
      <section className="dashboard-section" aria-labelledby="activity-heading">
        <div className="dashboard-section-header">
          <Clock size={16} className="text-violet-400" />
          <h2 id="activity-heading" className="dashboard-section-title">
            Recent Activity
          </h2>
        </div>
        <div className="activity-empty">
          <p className="activity-empty-text">No recent activity yet.</p>
          <p className="activity-empty-sub">
            Create a workflow and run a step to see activity here.
          </p>
        </div>
      </section>
    </div>
  );
}
