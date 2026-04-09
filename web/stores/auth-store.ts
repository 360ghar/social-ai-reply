import { create } from "zustand";
import type { AuthPayload } from "@/lib/api";

interface AuthState {
  token: string | null;
  user: AuthPayload["user"] | null;
  workspace: AuthPayload["workspace"] | null;
  loading: boolean;
  error: string | null;
  persist: (payload: AuthPayload) => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setToken: (token: string | null) => void;
}

const STORAGE_KEY = "redditflow-auth";
const LEGACY_STORAGE_KEY = "reply-radar-auth";

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  workspace: null,
  loading: true,
  error: null,

  persist(payload) {
    set({
      token: payload.access_token,
      user: payload.user,
      workspace: payload.workspace,
    });
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      window.localStorage.removeItem(LEGACY_STORAGE_KEY);
    }
  },

  clearAuth() {
    set({ token: null, user: null, workspace: null, error: null });
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem(LEGACY_STORAGE_KEY);
    }
  },

  setLoading(loading) {
    set({ loading });
  },

  setError(error) {
    set({ error });
  },

  setToken(token) {
    set({ token });
    if (typeof window !== "undefined" && token) {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        try {
          const stored = JSON.parse(raw) as AuthPayload;
          stored.access_token = token;
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
        } catch {
          // ignore
        }
      }
    }
  },
}));
