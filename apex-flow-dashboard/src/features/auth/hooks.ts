import { useAuthContext } from "@/features/auth/context";

/**
 * useAuth — primary auth hook for consuming auth state anywhere in the app.
 *
 * Usage:
 *   const { user, accessToken, isLoading } = useAuth();
 *
 * accessToken: attach as `Authorization: Bearer <accessToken>` to all backend API calls.
 */
export function useAuth() {
  return useAuthContext();
}
