import {
  GitBranch,
  Footprints,
  KeyRound,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowUpRight,
} from "lucide-react";
import type { DashboardStats, RecentActivity } from "../data";
import Link from "next/link";

const STATUS_ICON: Record<string, { icon: React.ElementType; cls: string }> = {
  completed: { icon: CheckCircle2, cls: "text-emerald-400" },
  failed:    { icon: AlertTriangle, cls: "text-red-400" },
  pending:   { icon: Clock, cls: "text-amber-400" },
  running:   { icon: GitBranch, cls: "text-cyan-400" },
};

import React from "react";

export function StatCards({ stats }: { stats: DashboardStats }) {
  const cards = [
    {
      id: "stat-workflows",
      label: "Total Workflows",
      value: stats.totalWorkflows,
      icon: GitBranch,
      color: "violet",
      hint: "Registered workflows",
      href: "/dashboard/workflows",
    },
    {
      id: "stat-steps-pending",
      label: "Pending Steps",
      value: stats.pendingSteps,
      icon: Clock,
      color: "amber",
      hint: "Awaiting a worker",
      href: "/dashboard/steps",
    },
    {
      id: "stat-steps-done",
      label: "Completed Steps",
      value: stats.completedSteps,
      icon: CheckCircle2,
      color: "emerald",
      hint: "Successfully processed",
      href: "/dashboard/steps",
    },
    {
      id: "stat-steps-failed",
      label: "Failed Steps",
      value: stats.failedSteps,
      icon: AlertTriangle,
      color: "red",
      hint: "Require attention",
      href: "/dashboard/steps",
    },
  ];

  return (
    <>
      {cards.map(({ id, label, value, icon: Icon, color, hint, href }) => (
        <Link key={id} id={id} href={href} className={`stat-card stat-card--${color}`}>
          <div className="stat-card-header">
            <span className="stat-card-label">{label}</span>
            <div className={`stat-card-icon stat-card-icon--${color}`}>
              <Icon size={14} />
            </div>
          </div>
          <p className="stat-card-value">{value.toLocaleString()}</p>
          <p className="stat-card-hint">{hint}</p>
        </Link>
      ))}
    </>
  );
}

export function ActivityFeed({ items }: { items: RecentActivity[] }) {
  return (
    <ul className="activity-list">
      {items.map((item) => {
        const cfg = STATUS_ICON[item.status ?? "pending"];
        const Icon = cfg?.icon ?? Clock;
        return (
          <li key={item.id} className="activity-item">
            <div className={`activity-icon-wrap ${cfg?.cls ?? ""}`}>
              <Icon size={13} />
            </div>
            <div className="activity-body">
              <p className="activity-label">{item.label}</p>
              <p className="activity-meta">{item.meta}</p>
            </div>
            <span className="activity-time">{item.timestamp}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function QuickNav() {
  const links = [
    { href: "/dashboard/workflows",   label: "Workflows",    desc: "Browse and trigger your workflows", icon: GitBranch, color: "violet" },
    { href: "/dashboard/steps",       label: "Steps",        desc: "Monitor step execution and errors",  icon: Footprints, color: "cyan" },
    { href: "/dashboard/project-keys", label: "Project Keys", desc: "Manage SDK worker authentication",   icon: KeyRound,   color: "amber" },
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
