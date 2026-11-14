"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, X } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/features/auth/hooks";
import { ProjectSelector } from "@/features/projects/components/ProjectSelector";

interface BreadcrumbItem {
  label: string;
  href: string;
}

const SECTION_LABELS: Record<string, string> = {
  steps: "steps",
  workers: "workers",
  "project-keys": "keys",
  settings: "settings",
};

function buildBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const trimmed = pathname.replace(/^\/dashboard\/?/, "");
  if (!trimmed) {
    return [{ label: "overview", href: "/dashboard" }];
  }

  const parts = trimmed.split("/").filter(Boolean);

  if (parts[0] === "workflows") {
    const items: BreadcrumbItem[] = [
      { label: "workflows", href: "/dashboard/workflows" },
    ];
    if (parts[1]) {
      items.push({
        label: decodeURIComponent(parts[1]),
        href: `/dashboard/workflows/${parts[1]}`,
      });
    }
    if (parts[2]) {
      items.push({
        label: parts[2].slice(0, 8),
        href: `/dashboard/workflows/${parts[1]}/${parts[2]}`,
      });
    }
    return items;
  }

  const root = parts[0];
  return [
    {
      label: SECTION_LABELS[root] ?? root,
      href: `/dashboard/${root}`,
    },
  ];
}

function getInitials(name?: string, email?: string): string {
  if (name) {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }
  if (email) return email.slice(0, 2).toUpperCase();
  return "??";
}

export function TopBar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [openNotifs, setOpenNotifs] = useState(false);

  const breadcrumbs = buildBreadcrumbs(pathname);

  return (
    <header className="console-topbar">
      <div className="console-topbar-left">
        <Link href="/dashboard" className="console-topbar-brand">
          <div className="console-topbar-logo">
            <svg width="16" height="16" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <path
                d="M14 2L24 8V20L14 26L4 20V8L14 2Z"
                fill="url(#hexGradTopbar)"
                stroke="rgba(139,92,246,0.45)"
                strokeWidth="1"
              />
              <path d="M14 7L19 10V16L14 19L9 16V10L14 7Z" fill="rgba(139,92,246,0.35)" />
              <defs>
                <linearGradient id="hexGradTopbar" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#8B5CF6" stopOpacity="0.85" />
                  <stop offset="1" stopColor="#06B6D4" stopOpacity="0.65" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span className="console-topbar-brand-name">ApexFlow</span>
        </Link>

        <span className="console-breadcrumb-sep" aria-hidden="true">
          /
        </span>

        <ProjectSelector />

        <nav className="console-breadcrumbs" aria-label="Breadcrumb">
          {breadcrumbs.map((crumb, idx) => {
            const isLast = idx === breadcrumbs.length - 1;
            return (
              <React.Fragment key={`${idx}-${crumb.label}`}>
                <span className="console-breadcrumb-sep" aria-hidden="true">
                  /
                </span>
                {isLast ? (
                  <span
                    className="console-breadcrumb-item active"
                    title={crumb.label}
                  >
                    {crumb.label}
                  </span>
                ) : (
                  <Link
                    href={crumb.href}
                    className="console-breadcrumb-item"
                    title={crumb.label}
                  >
                    {crumb.label}
                  </Link>
                )}
              </React.Fragment>
            );
          })}
        </nav>
      </div>

      <div className="console-topbar-right">
        <div className="relative">
          <button
            id="header-notifications-btn"
            onClick={() => setOpenNotifs((o) => !o)}
            className="console-topbar-icon-btn"
            aria-label="Notifications"
          >
            <Bell size={14} />
            <span className="console-topbar-badge">!</span>
          </button>

          {openNotifs && (
            <div className="absolute right-0 mt-2 w-80 bg-[#161620] border border-white/10 rounded-xl shadow-2xl p-4 z-50 animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
                <h4 className="text-xs font-bold text-[#ececee] tracking-wide uppercase">
                  System Notifications
                </h4>
                <button onClick={() => setOpenNotifs(false)} className="text-zinc-400 hover:text-white">
                  <X size={14} />
                </button>
              </div>

              <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20 text-center">
                <Bell size={20} className="mx-auto text-violet-400 mb-1.5 opacity-70" />
                <p className="text-xs font-semibold text-zinc-200">Notifications Unavailable</p>
                <p className="text-[11px] text-zinc-400 leading-relaxed mt-1">
                  Live WebSocket &amp; push notification dispatch is currently unavailable in this environment.
                </p>
                <span className="text-[10px] text-violet-300 font-mono mt-2 block bg-violet-950/60 py-1 px-2 rounded border border-violet-500/30">
                  Status: System Operational (Long-Polling Active)
                </span>
              </div>
            </div>
          )}
        </div>

        <Avatar className="h-7 w-7 cursor-pointer">
          <AvatarFallback className="bg-violet-900/60 text-violet-300 text-[11px] font-semibold">
            {getInitials(user?.user_metadata?.full_name, user?.email)}
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}

