"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { forgotPassword, resetPassword } from "@/lib/api";
import { supabase } from "@/lib/supabase";

function ResetPasswordContent() {
  const { success, error, warning } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [done, setDone] = useState(false);
  const [hasSession, setHasSession] = useState(false);
  const [checking, setChecking] = useState(true);

  // Check if Supabase established a session from the reset link
  useEffect(() => {
    async function checkSession() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session) {
        setHasSession(true);
      }
      setChecking(false);
    }
    checkSession();

    // Listen for auth events — Supabase fires PASSWORD_RECOVERY when user clicks reset link
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY" && session) {
        setHasSession(true);
        setChecking(false);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  async function handleRequest() {
    if (!email.trim()) {
      warning("Please enter your email.");
      return;
    }
    setLoading(true);
    try {
      await forgotPassword(email.trim().toLowerCase());
      setSent(true);
      success("Reset link sent!", "Check your email for the password reset link.");
    } catch (e: any) {
      error("Could not send reset email", e.message);
    }
    setLoading(false);
  }

  async function handleReset() {
    if (password.length < 8) {
      warning("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      warning("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(password);
      setDone(true);
      success("Password updated!", "You can now log in with your new password.");
    } catch (e: any) {
      error("Reset failed", e.message);
    }
    setLoading(false);
  }

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="flex w-full max-w-md justify-center rounded-xl border bg-card p-8 shadow-sm">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md rounded-xl border bg-card p-8 shadow-sm">
        <h2 className="mb-2 text-xl font-semibold">
          {hasSession ? "Set New Password" : "Reset Password"}
        </h2>

        {!hasSession && !sent && (
          <>
            <p className="mb-5 text-muted-foreground">
              Enter your email and we&apos;ll send you a reset link.
            </p>
            <div className="space-y-2">
              <Label htmlFor="reset-email">Email</Label>
              <Input
                id="reset-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
            <Button
              disabled={loading}
              onClick={handleRequest}
              className="mt-4 w-full"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Send Reset Link
            </Button>
            <p className="mt-4 text-center">
              <Link
                href="/login"
                className="text-sm text-muted-foreground hover:underline"
              >
                Back to login
              </Link>
            </p>
          </>
        )}

        {!hasSession && sent && (
          <div className="py-5 text-center">
            <div className="mb-4 text-5xl">&#x2709;&#xfe0f;</div>
            <h3 className="text-lg font-semibold">Check Your Email</h3>
            <p className="mt-2 text-muted-foreground">
              We sent a password reset link to <strong>{email}</strong>.
            </p>
            <p className="mt-4">
              <Link
                href="/login"
                className="text-sm text-muted-foreground hover:underline"
              >
                Back to login
              </Link>
            </p>
          </div>
        )}

        {hasSession && !done && (
          <>
            <p className="mb-5 text-muted-foreground">
              Enter your new password below.
            </p>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="new-password">New Password</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 characters"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm Password</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Type password again"
                />
              </div>
            </div>
            <Button
              disabled={loading}
              onClick={handleReset}
              className="mt-4 w-full"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Update Password
            </Button>
          </>
        )}

        {hasSession && done && (
          <div className="py-5 text-center">
            <div className="mb-4 text-5xl">&#x2705;</div>
            <h3 className="text-lg font-semibold">Password Updated!</h3>
            <p className="mt-2 text-muted-foreground">
              Your password has been changed. You can now log in.
            </p>
            <Button className="mt-4">
              <Link href="/login">Go to Login</Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background p-4">
          <div className="flex w-full max-w-md justify-center rounded-xl border bg-card p-8 shadow-sm">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
