"use client";

import { useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { apiRequest, isAuthError, type AuthPayload } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { persist, clearAuth, setLoading, setError, setToken } = useAuthStore();

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
            }
          }
        } else {
          const STORAGE_KEY = "redditflow-auth";
          const LEGACY_STORAGE_KEY = "reply-radar-auth";
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
          setToken(session.access_token);
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
  const store = useAuthStore();

  return {
    token: store.token,
    user: store.user,
    workspace: store.workspace,
    loading: store.loading,
    error: store.error,
    login: async (email: string, password: string) => {
      store.setError(null);
      const { data, error: sbError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (sbError || !data.session) {
        throw new Error(sbError?.message ?? "Invalid email or password.");
      }
      const payload = await apiRequest<AuthPayload>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      store.persist({ ...payload, access_token: data.session.access_token });
    },
    register: async (input: {
      email: string;
      password: string;
      fullName: string;
      workspaceName: string;
    }) => {
      store.setError(null);
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
      store.persist(payload);
    },
    logout: async () => {
      const currentToken = store.token;
      store.clearAuth();
      await supabase.auth.signOut();
      if (currentToken) {
        await apiRequest("/v1/auth/logout", { method: "POST" }, currentToken);
      }
    },
    refreshSession: async () => {
      const { data: { session } } = await supabase.auth.refreshSession();
      if (session?.access_token) {
        store.setToken(session.access_token);
      }
    },
  };
}
