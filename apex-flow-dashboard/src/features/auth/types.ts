import type { User } from "@supabase/supabase-js";

export interface AuthUser {
  id: string;
  email: string | undefined;
  user_metadata: {
    full_name?: string;
    avatar_url?: string;
  };
}

export interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
}

export interface LoginFormValues {
  email: string;
  password: string;
}

export interface SignupFormValues {
  email: string;
  password: string;
  fullName: string;
}

export function toAuthUser(user: User | null): AuthUser | null {
  if (!user) return null;
  return {
    id: user.id,
    email: user.email,
    user_metadata: {
      full_name: user.user_metadata?.full_name,
      avatar_url: user.user_metadata?.avatar_url,
    },
  };
}
