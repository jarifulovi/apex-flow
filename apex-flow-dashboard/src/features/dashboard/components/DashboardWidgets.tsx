import React from "react";
import {
  GitBranch,
  Footprints,
  KeyRound,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowUpRight,
  Activity,
  Loader2,
  Cpu,
  TrendingUp,
  Timer,
} from "lucide-react";
import Link from "next/link";
import type { DashboardStats, ActivityItem } from "@/features/dashboard/api";

const STATUS_ICON: Record<string, { icon: React.ElementType; cls: string }> = {
  success:   { icon: CheckCircle2, cls: "text-emerald-400" },
  completed: { icon: CheckCircle2, cls: "text-emerald-400" },
  failed:    { icon: AlertTriangle, cls: "text-red-400" },
  queued:    { icon: Clock, cls: "text-amber-400" },
  running:   { icon: Loader2, cls: "text-cyan-400 animate-spin" },
};

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function StatCards({ stats }: { stats: DashboardStats }) {
  const cards = [
    {
      id: "stat-workflows",
      label: "Total Workflows",
      value: stats.totalWorkflows.toLocaleString(),
      icon: GitBranch,
      color: "violet",
      hint: "Registered workflow runs",
    },
    {
      id: "stat-success-rate",
      label: "Success Rate",
      value: `${(stats.successRatePercent ?? 0).toFixed(1)}%`,
      icon: TrendingUp,
      color: "emerald",
      hint: "Terminal run completion rate",
    },
    {
      id: "stat-workers-active",
      label: "Active Workers",
      value: (stats.activeWorkersCount ?? 0).toLocaleString(),
      icon: Cpu,
      color: "cyan",
      hint: "Live polling SDK workers",
    },
    {
      id: "stat-avg-duration",
      label: "Avg Duration",
      value: (stats.avgDurationSeconds ?? 0) > 0 ? `${stats.avgDurationSeconds.toFixed(1)}s` : "—",
      icon: Timer,
      color: "amber",
      hint: "Completed execution avg time",
    },
  ];

  return (
    <>
      {cards.map(({ id, label, value, icon: Icon, color, hint }) => (
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
    </>
  );
}

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  if (items.length === 0) {
    return (
      <div className="p-8 text-center bg-[#161620]/75 border border-white/5 rounded-xl text-zinc-400">
        <Activity size={24} className="mx-auto mb-2 opacity-50" />
        <p className="text-sm font-medium text-zinc-300">No activity logged yet</p>
        <p className="text-xs text-zinc-500 mt-1">Workflow step updates will appear here in real-time.</p>
      </div>
    );
  }

  return (
    <ul className="activity-list">
      {items.map((item) => {
        const cfg = STATUS_ICON[item.status] || STATUS_ICON.queued;
        const Icon = cfg.icon;
        return (
          <li key={item.id} className="activity-item">
            <div className={`activity-icon-wrap ${cfg.cls}`}>
              <Icon size={13} />
            </div>
            <div className="activity-body">
              <p className="activity-label font-mono">
                Step <span className="text-violet-300 font-semibold">{item.stepName}</span> ({item.status})
              </p>
              <p className="activity-meta">
                Workflow #{item.workflowId.substring(0, 8)}
                {item.errorMessage ? ` — ${item.errorMessage}` : ""}
              </p>
            </div>
            <span className="activity-time">{formatDate(item.timestamp)}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function QuickNav() {
  const links = [
    { href: "/dashboard/workflows",   label: "Workflows",    desc: "Browse and inspect workflow runs", icon: GitBranch, color: "violet" },
    { href: "/dashboard/workers",     label: "Workers",      desc: "Connected SDK workers status",     icon: Cpu,       color: "cyan" },
    { href: "/dashboard/steps",       label: "Steps",        desc: "Monitor step execution queues",    icon: Footprints, color: "amber" },
    { href: "/dashboard/project-keys", label: "Project Keys", desc: "Manage worker authentication",    icon: KeyRound,   color: "violet" },
  ];

  return (
    <div className="quick-links">
      {links.map(({ href, label, desc, icon: Icon, color }) => (
        <Link key={href} href={href} className={`quick-link-card quick-link-card--${color}`}>
          <div className={`quick-link-icon quick-link-icon--${color}`}>
            <Icon size={17} />
          </div>
          <div className="quick-link-body">
            <p className="quick-link-label">{label}</p>
            <p className="quick-link-desc">{desc}</p>
          </div>
          <ArrowUpRight size={14} className="quick-link-arrow" />
        </Link>
      ))}
    </div>
  );
}
