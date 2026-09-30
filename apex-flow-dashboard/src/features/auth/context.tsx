"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import type { AuthUser } from "@/features/auth/types";
import { toAuthUser } from "@/features/auth/types";

interface AuthContextValue {
  user: AuthUser | null;
  session: Session | null;
  isLoading: boolean;
  /** Raw JWT access token — attach as Bearer to all backend API calls */
  accessToken: string | null;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  session: null,
  isLoading: true,
  accessToken: null,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const syncSession = useCallback((s: Session | null) => {
    setSession(s);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    // createClient() is only called client-side, never during SSR/prerender
    const supabase = createClient();

    supabase.auth.getSession().then(({ data }) => syncSession(data.session));

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      syncSession(s);
    });

    return () => subscription.unsubscribe();
  }, [syncSession]);

  return (
    <AuthContext.Provider
      value={{
        user: toAuthUser(session?.user ?? null),
        session,
        isLoading,
        accessToken: session?.access_token ?? null,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  return useContext(AuthContext);
}
