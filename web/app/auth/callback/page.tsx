"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { apiRequest, isSetupRequired, type AuthPayload } from "@/lib/api";
import { Spinner } from "@/components/ui";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function handleCallback() {
      // Wait for Supabase to establish the session from the URL hash/params
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError || !session?.access_token) {
        // Listen for the auth state change event as fallback
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
          async (event, newSession) => {
            if (cancelled) return;
            if (event === "SIGNED_IN" && newSession?.access_token) {
              subscription.unsubscribe();
              await resolveSession(newSession.access_token);
            }
          }
        );

        // Timeout after 10 seconds
        setTimeout(() => {
          if (!cancelled) {
            subscription.unsubscribe();
            setError("Authentication timed out. Please try again.");
          }
        }, 10000);

        return;
      }

      await resolveSession(session.access_token);
    }

    async function resolveSession(accessToken: string) {
      if (cancelled) return;
      try {
        // Check if user has a local account
        const payload = await apiRequest<AuthPayload>("/v1/auth/me", {}, accessToken);
        // User exists — persist and go to dashboard
        const stored = { ...payload, access_token: accessToken };
        window.localStorage.setItem("redditflow-auth", JSON.stringify(stored));
        router.replace("/app/dashboard");
      } catch (err) {
        if (isSetupRequired(err)) {
          // First-time OAuth user — needs workspace setup
          router.replace("/auth/setup");
        } else {
          setError(err instanceof Error ? err.message : "Authentication failed. Please try again.");
        }
      }
    }

    handleCallback();

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (error) {
    return (
      <div className="auth-shell">
        <div className="auth-card" style={{ textAlign: "center" }}>
          <h2 style={{ marginBottom: 12 }}>Sign-in Failed</h2>
          <p className="text-muted" style={{ marginBottom: 20 }}>{error}</p>
          <a href="/login" className="primary-button" style={{ display: "inline-block", textDecoration: "none" }}>
            Back to Login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card" style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: 48 }}>
        <Spinner size="lg" />
        <p className="text-muted" style={{ marginTop: 16 }}>Completing sign-in...</p>
      </div>
    </div>
  );
}
