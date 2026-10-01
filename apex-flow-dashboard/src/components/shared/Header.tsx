"use client";

import React from "react";
import { Bell } from "lucide-react";
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

  return (
    <header className="dashboard-header">
      <div className="dashboard-header-left">
        <h1 className="dashboard-header-title">{title}</h1>
        {subtitle && <p className="dashboard-header-subtitle">{subtitle}</p>}
      </div>
      <div className="dashboard-header-right">
        {actions && <div className="header-actions">{actions}</div>}

        <button
          id="header-notifications-btn"
          className="dashboard-header-icon-btn"
          aria-label="Notifications"
        >
          <Bell size={15} />
          <span className="dashboard-header-badge">3</span>
        </button>

        <Avatar className="h-8 w-8 cursor-pointer">
          <AvatarFallback className="bg-violet-900/60 text-violet-300 text-xs font-semibold">
            {getInitials(user?.user_metadata?.full_name, user?.email)}
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
