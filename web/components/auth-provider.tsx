"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { apiRequest, isAuthError, type AuthPayload } from "../lib/api";

type AuthContextValue = {
  token: string | null;
  user: AuthPayload["user"] | null;
  workspace: AuthPayload["workspace"] | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (input: { email: string; password: string; fullName: string; workspaceName: string }) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const STORAGE_KEY = "redditflow-auth";
const LEGACY_STORAGE_KEY = "reply-radar-auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthPayload["user"] | null>(null);
  const [workspace, setWorkspace] = useState<AuthPayload["workspace"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Persist auth payload to local storage for fast reload
  function persist(payload: AuthPayload) {
    setToken(payload.access_token);
    setUser(payload.user);
    setWorkspace(payload.workspace);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
  }

  function clearAuth() {
    setToken(null);
    setUser(null);
    setWorkspace(null);
    setError(null);
    window.localStorage.removeItem(STORAGE_KEY);
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
  }

  // On mount: check for existing Supabase session, then validate with backend
  useEffect(() => {
    async function init() {
      try {
        // Check if Supabase has an active session (handles token refresh automatically)
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          // Validate with our backend and get user/workspace info
          try {
            const payload = await apiRequest<AuthPayload>(
              "/v1/auth/me",
              {},
              session.access_token
            );
            // Use the Supabase token (which is the real session token)
            persist({ ...payload, access_token: session.access_token });
          } catch (err) {
            if (isAuthError(err)) {
              // Token is valid with Supabase but user doesn't exist in our DB
              await supabase.auth.signOut();
              clearAuth();
            }
            // Network/server errors — keep existing local state if available
          }
        } else {
          // No Supabase session — check legacy local storage
          const raw = window.localStorage.getItem(STORAGE_KEY) ?? window.localStorage.getItem(LEGACY_STORAGE_KEY);
          if (raw) {
            // Old local-auth token — clear it, user needs to re-authenticate
            clearAuth();
          }
        }
      } catch {
        // Supabase client error — clear state
        clearAuth();
      } finally {
        setLoading(false);
      }
    }
    init();

    // Listen for Supabase auth state changes (e.g. token refresh, sign out from another tab)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === "SIGNED_OUT" || !session) {
          clearAuth();
        } else if (event === "TOKEN_REFRESHED" && session?.access_token) {
          setToken(session.access_token);
          // Update stored payload with new token
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

    // Sign in via Supabase
    const { data, error: sbError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (sbError || !data.session) {
      throw new Error(sbError?.message ?? "Invalid email or password.");
    }

    // Get user/workspace from our backend
    const payload = await apiRequest<AuthPayload>(
      "/v1/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }
    );

    persist({ ...payload, access_token: data.session.access_token });
  }

  async function register(input: { email: string; password: string; fullName: string; workspaceName: string }) {
    setError(null);

    // Register through our backend (which calls Supabase + creates workspace)
    const payload = await apiRequest<AuthPayload>("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: input.email,
        password: input.password,
        full_name: input.fullName,
        workspace_name: input.workspaceName,
      }),
    });

    // Also set the Supabase client session so it can handle token refresh
    if (payload.access_token && payload.refresh_token) {
      await supabase.auth.setSession({
        access_token: payload.access_token,
        refresh_token: payload.refresh_token,
      });
    }

    persist(payload);
  }

  async function logout() {
    await supabase.auth.signOut();
    clearAuth();
  }

  const refreshSession = useCallback(async () => {
    const { data: { session } } = await supabase.auth.refreshSession();
    if (session?.access_token) {
      setToken(session.access_token);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, workspace, loading, error, login, register, logout, refreshSession }}>
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
