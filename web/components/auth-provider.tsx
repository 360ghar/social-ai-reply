"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { apiRequest, type AuthPayload } from "../lib/api";

type AuthContextValue = {
  token: string | null;
  user: AuthPayload["user"] | null;
  workspace: AuthPayload["workspace"] | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (input: { email: string; password: string; fullName: string; workspaceName: string }) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const STORAGE_KEY = "redditflow-auth";
const LEGACY_STORAGE_KEY = "reply-radar-auth";

function isAuthError(error: unknown) {
  if (!(error instanceof Error)) {
    return false;
  }
  return [
    "Authentication required.",
    "Invalid token.",
    "User not found.",
    "No workspace membership found."
  ].includes(error.message);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthPayload["user"] | null>(null);
  const [workspace, setWorkspace] = useState<AuthPayload["workspace"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY) ?? window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) {
      setLoading(false);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as AuthPayload;
      setToken(parsed.access_token);
      setUser(parsed.user);
      setWorkspace(parsed.workspace);
      window.localStorage.removeItem(LEGACY_STORAGE_KEY);
      void refresh(parsed.access_token);
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem(LEGACY_STORAGE_KEY);
      setLoading(false);
    }
  }, []);

  async function refresh(activeToken: string) {
    try {
      const payload = await apiRequest<AuthPayload>("/v1/auth/me", {}, activeToken);
      persist(payload);
    } catch (err) {
      if (isAuthError(err)) {
        logout();
      } else {
        setError(err instanceof Error ? err.message : "Could not refresh your session.");
      }
    } finally {
      setLoading(false);
    }
  }

  function persist(payload: AuthPayload) {
    setToken(payload.access_token);
    setUser(payload.user);
    setWorkspace(payload.workspace);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
  }

  async function login(email: string, password: string) {
    setError(null);
    const payload = await apiRequest<AuthPayload>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    persist(payload);
  }

  async function register(input: { email: string; password: string; fullName: string; workspaceName: string }) {
    setError(null);
    const payload = await apiRequest<AuthPayload>("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: input.email,
        password: input.password,
        full_name: input.fullName,
        workspace_name: input.workspaceName
      })
    });
    persist(payload);
  }

  function logout() {
    setToken(null);
    setUser(null);
    setWorkspace(null);
    setError(null);
    window.localStorage.removeItem(STORAGE_KEY);
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
  }

  return (
    <AuthContext.Provider value={{ token, user, workspace, loading, error, login, register, logout }}>
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
