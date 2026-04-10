"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useToast } from "@/stores/toast";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { forgotPassword, resetPassword } from "@/lib/api";
import { supabase } from "@/lib/supabase";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function ResetPasswordContent() {
  const { success, error } = useToast();
  const emailRef = useRef<HTMLInputElement>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [done, setDone] = useState(false);
  const [hasSession, setHasSession] = useState(false);
  const [checking, setChecking] = useState(true);

  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [emailTouched, setEmailTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [confirmTouched, setConfirmTouched] = useState(false);

  useEffect(() => {
    async function checkSession() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session) setHasSession(true);
      setChecking(false);
    }
    checkSession();

    // Supabase fires PASSWORD_RECOVERY when the user clicks the reset link.
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

  useEffect(() => {
    if (!checking && !hasSession && !sent) emailRef.current?.focus();
  }, [checking, hasSession, sent]);

  function validateEmail(v: string): string {
    if (!v.trim()) return "Email is required.";
    if (!EMAIL_RE.test(v.trim())) return "Please enter a valid email.";
    return "";
  }

  function validatePassword(v: string): string {
    if (!v) return "Password is required.";
    if (v.length < 8) return "Must be at least 8 characters.";
    return "";
  }

  function validateConfirm(v: string): string {
    if (!v) return "Please confirm your password.";
    if (v !== password) return "Passwords do not match.";
    return "";
  }

  async function handleRequest() {
    const err = validateEmail(email);
    setEmailError(err);
    setEmailTouched(true);
    if (err) return;
    setLoading(true);
    try {
      await forgotPassword(email.trim().toLowerCase());
      setSent(true);
      success(
        "Reset link sent!",
        "Check your email for the password reset link.",
      );
    } catch (e: any) {
      error("Could not send reset email", e.message);
    }
    setLoading(false);
  }

  async function handleReset() {
    const pErr = validatePassword(password);
    const cErr = validateConfirm(confirm);
    setPasswordError(pErr);
    setConfirmError(cErr);
    setPasswordTouched(true);
    setConfirmTouched(true);
    if (pErr || cErr) return;
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
                ref={emailRef}
                id="reset-email"
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (emailTouched)
                    setEmailError(validateEmail(e.target.value));
                }}
                onBlur={() => {
                  setEmailTouched(true);
                  setEmailError(validateEmail(email));
                }}
                placeholder="you@example.com"
                aria-invalid={emailTouched && !!emailError}
              />
              {emailTouched && emailError && (
                <p className="text-xs text-destructive">{emailError}</p>
              )}
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
                  onChange={(e) => {
                    const v = e.target.value;
                    setPassword(v);
                    if (passwordTouched) setPasswordError(validatePassword(v));
                    if (confirmTouched && confirm)
                      setConfirmError(
                        confirm !== v ? "Passwords do not match." : "",
                      );
                  }}
                  onBlur={() => {
                    setPasswordTouched(true);
                    setPasswordError(validatePassword(password));
                  }}
                  placeholder="Min 8 characters"
                  autoComplete="new-password"
                  aria-invalid={passwordTouched && !!passwordError}
                />
                {passwordTouched && passwordError && (
                  <p className="text-xs text-destructive">{passwordError}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm Password</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={confirm}
                  onChange={(e) => {
                    const v = e.target.value;
                    setConfirm(v);
                    if (confirmTouched)
                      setConfirmError(
                        v !== password ? "Passwords do not match." : "",
                      );
                  }}
                  onBlur={() => {
                    setConfirmTouched(true);
                    setConfirmError(validateConfirm(confirm));
                  }}
                  placeholder="Type password again"
                  autoComplete="new-password"
                  aria-invalid={confirmTouched && !!confirmError}
                />
                {confirmTouched && confirmError && (
                  <p className="text-xs text-destructive">{confirmError}</p>
                )}
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
            <Link
              href="/login"
              className={`${buttonVariants()} mt-4 inline-flex`}
            >
              Go to Login
            </Link>
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
