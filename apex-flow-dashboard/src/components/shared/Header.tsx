"use client";

import React, { useState } from "react";
import { Bell, CheckCircle2, ShieldAlert, X } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/features/auth/hooks";

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

function getInitials(name?: string, email?: string): string {
  if (name) return name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2);
  if (email) return email.slice(0, 2).toUpperCase();
  return "??";
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  const { user } = useAuth();
  const [openNotifs, setOpenNotifs] = useState(false);

  const alerts = [
    {
      id: "1",
      title: "System Operational",
      desc: "FastAPI backend & database connection active",
      time: "Just now",
      icon: CheckCircle2,
      color: "text-emerald-400",
    },
    {
      id: "2",
      title: "Worker Authentication",
      desc: "Generate project keys in Dashboard to connect python SDK workers",
      time: "10m ago",
      icon: ShieldAlert,
      color: "text-violet-400",
    },
  ];

  return (
    <header className="dashboard-header">
      <div className="dashboard-header-left">
        <h1 className="dashboard-header-title">{title}</h1>
        {subtitle && <p className="dashboard-header-subtitle">{subtitle}</p>}
      </div>
      <div className="dashboard-header-right">
        {actions && <div className="header-actions">{actions}</div>}

        <div className="relative">
          <button
            id="header-notifications-btn"
            onClick={() => setOpenNotifs((o) => !o)}
            className="dashboard-header-icon-btn"
            aria-label="Notifications"
          >
            <Bell size={15} />
            <span className="dashboard-header-badge">{alerts.length}</span>
          </button>

          {openNotifs && (
            <div className="absolute right-0 mt-2 w-80 bg-[#161620] border border-white/10 rounded-xl shadow-2xl p-4 z-50 animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-3">
                <h4 className="text-xs font-bold text-[#ececee] tracking-wide uppercase">System Alerts</h4>
                <button onClick={() => setOpenNotifs(false)} className="text-zinc-400 hover:text-white">
                  <X size={14} />
                </button>
              </div>

              <div className="flex flex-col gap-2.5">
                {alerts.map(({ id, title: aTitle, desc, time, icon: Icon, color }) => (
                  <div key={id} className="flex items-start gap-2.5 p-2 rounded-lg bg-white/5 border border-white/5">
                    <Icon size={16} className={`${color} shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-zinc-200">{aTitle}</p>
                      <p className="text-[11px] text-zinc-400 leading-tight">{desc}</p>
                      <span className="text-[10px] text-zinc-500 mt-1 block">{time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <Avatar className="h-8 w-8 cursor-pointer">
          <AvatarFallback className="bg-violet-900/60 text-violet-300 text-xs font-semibold">
            {getInitials(user?.user_metadata?.full_name, user?.email)}
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
