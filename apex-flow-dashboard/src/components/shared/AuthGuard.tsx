"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/hooks";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * AuthGuard — wraps protected routes.
 * Redirects unauthenticated users to /auth/login.
 * Shows a loading spinner while session is being hydrated.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/auth/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="auth-logo-mark">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <path d="M14 2L24 8V20L14 26L4 20V8L14 2Z" fill="url(#hexGradSpinner)" stroke="rgba(139,92,246,0.4)" strokeWidth="1" />
              <path d="M14 7L19 10V16L14 19L9 16V10L14 7Z" fill="rgba(139,92,246,0.3)" />
              <defs>
                <linearGradient id="hexGradSpinner" x1="4" y1="2" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#8B5CF6" stopOpacity="0.8" />
                  <stop offset="1" stopColor="#06B6D4" stopOpacity="0.6" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <p className="text-sm text-zinc-500 animate-pulse">Loading…</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return <>{children}</>;
}
