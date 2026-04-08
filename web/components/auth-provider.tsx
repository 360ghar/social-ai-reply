"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { apiRequest, isAuthError, isSetupRequired, type AuthPayload } from "../lib/api";

type AuthContextValue = {
  token: string | null;
  user: AuthPayload["user"] | null;
  workspace: AuthPayload["workspace"] | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (input: { email: string; password: string; fullName: string; workspaceName: string }) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  completeOAuthSetup: (workspaceName: string) => Promise<AuthPayload>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
export const STORAGE_KEY = "redditflow-auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthPayload["user"] | null>(null);
  const [workspace, setWorkspace] = useState<AuthPayload["workspace"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function persist(payload: AuthPayload, accessToken?: string) {
    const tkn = accessToken || payload.access_token;
    setToken(tkn);
    setUser(payload.user);
    setWorkspace(payload.workspace);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...payload, access_token: tkn }));
  }

  function clearAuth() {
    setToken(null);
    setUser(null);
    setWorkspace(null);
    setError(null);
    window.localStorage.removeItem(STORAGE_KEY);
  }

  // On mount: check for existing Supabase session, then validate with backend
  useEffect(() => {
    async function init() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          try {
            const payload = await apiRequest<AuthPayload>(
              "/v1/auth/me",
              {},
              session.access_token
            );
            persist(payload, session.access_token);
          } catch (err) {
            if (isAuthError(err)) {
              await supabase.auth.signOut();
              clearAuth();
            } else if (isSetupRequired(err)) {
              // User exists in Supabase but not locally — don't clear session,
              // the callback/setup page will handle this.
              clearAuth();
            } else {
              // Unexpected error (network, server) — fail-safe to logged-out
              clearAuth();
            }
          }
        } else {
          // No Supabase session — clear any stale local state
          clearAuth();
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
          const raw = window.localStorage.getItem(STORAGE_KEY);
          if (raw) {
            try {
              const stored = JSON.parse(raw) as AuthPayload;
              stored.access_token = session.access_token;
              window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
            } catch {
              // ignore
            }
          }
        }
      }
    );

    return () => { subscription.unsubscribe(); };
  }, []);

  async function login(email: string, password: string) {
    setError(null);

    // Authenticate with Supabase
    const { data, error: sbError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (sbError || !data.session) {
      throw new Error(sbError?.message ?? "Invalid email or password.");
    }

    // Get user/workspace from backend (no re-authentication needed)
    const payload = await apiRequest<AuthPayload>(
      "/v1/auth/me",
      {},
      data.session.access_token
    );

    persist(payload, data.session.access_token);
  }

  async function register(input: { email: string; password: string; fullName: string; workspaceName: string }) {
    setError(null);

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

    persist(payload);
  }

  async function loginWithGoogle() {
    setError(null);
    const { error: sbError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (sbError) {
      throw new Error(sbError.message ?? "Could not start Google sign-in.");
    }
    // Browser redirects to Google — no further action here
  }

  async function completeOAuthSetup(workspaceName: string): Promise<AuthPayload> {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) {
      throw new Error("No active session. Please sign in again.");
    }

    const payload = await apiRequest<AuthPayload>(
      "/v1/auth/oauth-complete",
      {
        method: "POST",
        body: JSON.stringify({ workspace_name: workspaceName }),
      },
      session.access_token
    );

    persist(payload, session.access_token);
    return payload;
  }

  async function logout() {
    const currentToken = token;
    clearAuth();
    await supabase.auth.signOut();

    if (currentToken) {
      try {
        await apiRequest("/v1/auth/logout", { method: "POST" }, currentToken);
      } catch {
        // Best-effort server-side revocation
      }
    }
  }

  const refreshSession = useCallback(async () => {
    const { data: { session } } = await supabase.auth.refreshSession();
    if (session?.access_token) {
      setToken(session.access_token);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, workspace, loading, error, login, register, loginWithGoogle, completeOAuthSetup, logout, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
