"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  GitBranch,
  Footprints,
  Cpu,
  KeyRound,
  Settings,
  LogOut,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/features/auth/hooks";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const COLLAPSE_STORAGE_KEY = "apexflow_sidebar_collapsed";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/workflows", label: "Workflows", icon: GitBranch },
  { href: "/dashboard/steps", label: "Steps", icon: Footprints },
  { href: "/dashboard/workers", label: "Workers", icon: Cpu },
  { href: "/dashboard/project-keys", label: "Project Keys", icon: KeyRound },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

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

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem(COLLAPSE_STORAGE_KEY) === "true");
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSE_STORAGE_KEY, String(next));
      return next;
    });
  }

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/auth/login");
  }

  return (
    <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
      <nav className="sidebar-nav" aria-label="Main navigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive =
            pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={`sidebar-nav-item${isActive ? " active" : ""}`}
            >
              <Icon size={16} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
              {!collapsed && isActive && (
                <ChevronRight size={12} className="ml-auto opacity-60" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && (
          <div className="sidebar-user">
            <Avatar className="h-7 w-7 shrink-0">
              <AvatarFallback className="bg-violet-900/60 text-violet-300 text-[10px] font-semibold">
                {getInitials(user?.user_metadata?.full_name, user?.email)}
              </AvatarFallback>
            </Avatar>
            <div className="sidebar-user-info">
              <p className="sidebar-user-name">
                {user?.user_metadata?.full_name ?? "User"}
              </p>
              <p className="sidebar-user-email">{user?.email}</p>
            </div>
          </div>
        )}
        <div className="sidebar-footer-actions">
          <button
            id="sidebar-collapse-btn"
            onClick={toggleCollapsed}
            className="sidebar-collapse-btn"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
          </button>
          <button
            id="sidebar-logout-btn"
            onClick={handleLogout}
            className="sidebar-logout-btn"
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
