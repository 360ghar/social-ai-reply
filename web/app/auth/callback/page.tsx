"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { apiRequest, isSetupRequired, type AuthPayload } from "@/lib/api";
import { STORAGE_KEY } from "@/stores/auth-store";
import { buttonVariants } from "@/components/ui/button";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    async function resolveSession(accessToken: string) {
      if (cancelled) return;
      try {
        const payload = await apiRequest<AuthPayload>(
          "/v1/auth/me",
          {},
          accessToken,
        );
        const stored = { ...payload, access_token: accessToken };
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
        router.replace("/app/dashboard");
      } catch (err) {
        if (isSetupRequired(err)) {
          router.replace("/auth/setup");
        } else {
          setError(
            err instanceof Error
              ? err.message
              : "Authentication failed. Please try again.",
          );
        }
      }
    }

    async function handleCallback() {
      const {
        data: { session },
        error: sessionError,
      } = await supabase.auth.getSession();

      if (sessionError || !session?.access_token) {
        // Fallback: listen for the auth state change event.
        const {
          data: { subscription },
        } = supabase.auth.onAuthStateChange(async (event, newSession) => {
          if (cancelled) return;
          if (event === "SIGNED_IN" && newSession?.access_token) {
            subscription.unsubscribe();
            await resolveSession(newSession.access_token);
          }
        });

        timeoutId = setTimeout(() => {
          if (!cancelled) {
            subscription.unsubscribe();
            setError("Authentication timed out. Please try again.");
          }
        }, 10000);

        return;
      }

      await resolveSession(session.access_token);
    }

    handleCallback();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-md rounded-xl border bg-card p-8 text-center shadow-sm">
          <h2 className="mb-3 text-xl font-semibold">Sign-in Failed</h2>
          <p className="mb-5 text-muted-foreground">{error}</p>
          <Link href="/login" className={buttonVariants()}>
            Back to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="flex w-full max-w-md flex-col items-center rounded-xl border bg-card p-12 shadow-sm">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-4 text-muted-foreground">Completing sign-in...</p>
      </div>
    </div>
  );
}
