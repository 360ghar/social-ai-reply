"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  apiRequest,
  isAuthError,
  isSetupRequired,
  type AuthPayload,
} from "@/lib/api";
import {
  useAuthStore,
  STORAGE_KEY,
  LEGACY_STORAGE_KEY,
} from "@/stores/auth-store";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { persist, clearAuth, setLoading, setError, setToken } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    async function init() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          try {
            const payload = await apiRequest<AuthPayload>(
              "/v1/auth/me",
              {},
              session.access_token,
            );
            persist({ ...payload, access_token: session.access_token });
          } catch (err) {
            if (isAuthError(err)) {
              await supabase.auth.signOut();
              clearAuth();
            } else if (isSetupRequired(err)) {
              // User is authenticated with Supabase but has no local
              // account (first-time OAuth user or DB reset). Do NOT sign
              // them out of Supabase — /auth/setup needs the live session
              // to complete workspace provisioning.
              clearAuth();
              router.replace("/auth/setup");
            } else {
              clearAuth();
            }
          }
        } else {
          const raw =
            window.localStorage.getItem(STORAGE_KEY) ??
            window.localStorage.getItem(LEGACY_STORAGE_KEY);
          if (raw) {
            clearAuth();
          }
        }
      } catch {
        clearAuth();
      } finally {
        setLoading(false);
      }
    }
    init();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === "SIGNED_OUT" || !session) {
          clearAuth();
        } else if (event === "TOKEN_REFRESHED" && session?.access_token) {
          // Re-validate with backend to catch deactivation or other server-side changes
          try {
            const payload = await apiRequest<AuthPayload>(
              "/v1/auth/me",
              {},
              session.access_token,
            );
            persist({ ...payload, access_token: session.access_token });
          } catch (err) {
            if (isAuthError(err)) {
              await supabase.auth.signOut();
              clearAuth();
            } else if (isSetupRequired(err)) {
              clearAuth();
              router.replace("/auth/setup");
            } else {
              // Non-auth errors (network) — persist the new token before handling error
              setToken(session.access_token);
              // Next API call will handle the network error
            }
          }
        }
      },
    );

    return () => {
      subscription.unsubscribe();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <>{children}</>;
}

export function useAuth() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const workspace = useAuthStore((s) => s.workspace);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const storeSetError = useAuthStore((s) => s.setError);
  const storePersist = useAuthStore((s) => s.persist);
  const storeClearAuth = useAuthStore((s) => s.clearAuth);
  const storeSetToken = useAuthStore((s) => s.setToken);

  const methods = useMemo(
    () => ({
      login: async (email: string, password: string) => {
        storeSetError(null);
        const { data, error: sbError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (sbError || !data.session) {
          throw new Error(sbError?.message ?? "Invalid email or password.");
        }
        // The backend /v1/auth/login route was removed; /v1/auth/me
        // returns the same user + workspace payload and validates the
        // Supabase JWT directly.
        try {
          const payload = await apiRequest<AuthPayload>(
            "/v1/auth/me",
            {},
            data.session.access_token,
          );
          storePersist({ ...payload, access_token: data.session.access_token });
        } catch (err) {
          if (isSetupRequired(err)) {
            // Local account missing (e.g., DB reset). Keep Supabase session
            // alive so /auth/setup can complete provisioning.
            throw new Error("SETUP_REQUIRED");
          }
          throw err;
        }
      },
      loginWithGoogle: async () => {
        storeSetError(null);
        const { error: sbError } = await supabase.auth.signInWithOAuth({
          provider: "google",
          options: {
            redirectTo: `${window.location.origin}/auth/callback`,
          },
        });
        if (sbError) {
          throw new Error(sbError.message ?? "Could not start Google sign-in.");
        }
        // Browser redirects to Google — no further action here.
      },
      completeOAuthSetup: async (
        workspaceName: string,
      ): Promise<AuthPayload> => {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session?.access_token) {
          throw new Error("No active session. Please sign in again.");
        }
        const payload = await apiRequest<AuthPayload>(
          "/v1/auth/oauth-complete",
          {
            method: "POST",
            body: JSON.stringify({ workspace_name: workspaceName }),
          },
          session.access_token,
        );
        storePersist({ ...payload, access_token: session.access_token });
        return payload;
      },
      register: async (input: {
        email: string;
        password: string;
        fullName: string;
        workspaceName: string;
      }) => {
        storeSetError(null);
        const payload = await apiRequest<AuthPayload>("/v1/auth/register", {
          method: "POST",
          body: JSON.stringify({
            email: input.email,
            password: input.password,
            full_name: input.fullName,
            workspace_name: input.workspaceName,
          }),
        });
        if (payload.access_token && payload.refresh_token) {
          await supabase.auth.setSession({
            access_token: payload.access_token,
            refresh_token: payload.refresh_token,
          });
        }
        storePersist(payload);
      },
      logout: async () => {
        const currentToken = token;
        storeClearAuth();
        await supabase.auth.signOut();
        if (currentToken) {
          await apiRequest("/v1/auth/logout", { method: "POST" }, currentToken);
        }
      },
      refreshSession: async () => {
        const { data: { session } } = await supabase.auth.refreshSession();
        if (session?.access_token) {
          storeSetToken(session.access_token);
        }
      },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token, storeSetError, storePersist, storeClearAuth, storeSetToken],
  );

  return { token, user, workspace, loading, error, ...methods };
}
