"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  GitBranch,
  Footprints,
  Cpu,
  KeyRound,
  Settings,
  LogOut,
  ChevronRight,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/features/auth/hooks";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useRouter } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/workflows", label: "Workflows", icon: GitBranch },
  { href: "/dashboard/steps", label: "Steps", icon: Footprints },
  { href: "/dashboard/workers", label: "Workers", icon: Cpu },
  { href: "/dashboard/project-keys", label: "Project Keys", icon: KeyRound },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

function getInitials(name?: string, email?: string): string {
  if (name) return name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);
  if (email) return email.slice(0, 2).toUpperCase();
  return "??";
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/auth/login");
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <svg width="20" height="20" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <path d="M14 2L24 8V20L14 26L4 20V8L14 2Z" fill="url(#hexGradSidebar)" stroke="rgba(139,92,246,0.4)" strokeWidth="1" />
            <path d="M14 7L19 10V16L14 19L9 16V10L14 7Z" fill="rgba(139,92,246,0.3)" />
            <defs>
              <linearGradient id="hexGradSidebar" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                <stop stopColor="#8B5CF6" stopOpacity="0.8" />
                <stop offset="1" stopColor="#06B6D4" stopOpacity="0.6" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span className="sidebar-brand-name">ApexFlow</span>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav" aria-label="Main navigation">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link key={href} href={href} className={`sidebar-nav-item${isActive ? " active" : ""}`}>
              <Icon size={16} className="shrink-0" />
              <span>{label}</span>
              {isActive && <ChevronRight size={12} className="ml-auto opacity-60" />}
            </Link>
          );
        })}
      </nav>

      {/* User + Logout */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <Avatar className="h-7 w-7 shrink-0">
            <AvatarFallback className="bg-violet-900/60 text-violet-300 text-[10px] font-semibold">
              {getInitials(user?.user_metadata?.full_name, user?.email)}
            </AvatarFallback>
          </Avatar>
          <div className="sidebar-user-info">
            <p className="sidebar-user-name">{user?.user_metadata?.full_name ?? "User"}</p>
            <p className="sidebar-user-email">{user?.email}</p>
          </div>
        </div>
        <button
          id="sidebar-logout-btn"
          onClick={handleLogout}
          className="sidebar-logout-btn"
          aria-label="Sign out"
        >
          <LogOut size={15} />
        </button>
      </div>
    </aside>
  );
}
