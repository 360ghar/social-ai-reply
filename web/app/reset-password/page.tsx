"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useToast } from "@/stores/toast";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Mail, CheckCircle2, Eye, EyeOff } from "lucide-react";
import { forgotPassword, resetPassword } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { getErrorMessage } from "@/types/errors";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/* ---------- Branded left panel ---------- */
function BrandPanel() {
  return (
    <div className="hidden md:flex md:w-1/2 flex-col items-center justify-center bg-gradient-to-br from-[#0e1930] to-[#1a2744] p-12 text-center">
      <Link href="/" className="mb-4 text-2xl font-bold text-white">
        RedditFlow
      </Link>
      <p className="max-w-xs text-base leading-relaxed text-white/70">
        Find your audience. Engage authentically. Grow on Reddit.
      </p>
      <div className="pointer-events-none absolute bottom-0 left-0 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-white/5 blur-3xl" />
    </div>
  );
}

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
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

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
    } catch (err: unknown) {
      error("Could not send reset email", getErrorMessage(err));
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
    } catch (err: unknown) {
      error("Reset failed", getErrorMessage(err));
    }
    setLoading(false);
  }

  /* ---------- Checking session spinner ---------- */
  if (checking) {
    return (
      <div className="flex min-h-screen">
        <BrandPanel />
        <div className="flex w-full items-center justify-center md:w-1/2">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  /* ---------- Main layout ---------- */
  function formWrapper(children: React.ReactNode) {
    return (
      <div className="flex min-h-screen">
        <BrandPanel />
        <div className="flex w-full flex-col items-center justify-center px-6 py-12 md:w-1/2">
          {/* Mobile-only slim header */}
          <div className="mb-8 md:hidden">
            <Link href="/" className="text-xl font-bold text-primary">
              RedditFlow
            </Link>
          </div>
          <div className="w-full max-w-sm">{children}</div>
        </div>
      </div>
    );
  }

  /* State 1: Request reset */
  if (!hasSession && !sent) {
    return formWrapper(
      <>
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Reset Password</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter your email and we&apos;ll send you a reset link.
          </p>
        </div>
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
          className="mt-6 w-full"
          size="lg"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Sending...
            </>
          ) : (
            "Send Reset Link"
          )}
        </Button>
        <p className="mt-6 text-center">
          <Link
            href="/login"
            className="text-sm text-muted-foreground hover:underline"
          >
            Back to login
          </Link>
        </p>
      </>,
    );
  }

  /* State 2: Confirmation email sent */
  if (!hasSession && sent) {
    return formWrapper(
      <div className="py-8 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
          <Mail className="h-7 w-7 text-primary" />
        </div>
        <h3 className="text-xl font-semibold">Check Your Email</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          We sent a password reset link to <strong>{email}</strong>.
        </p>
        <p className="mt-6">
          <Link
            href="/login"
            className="text-sm text-muted-foreground hover:underline"
          >
            Back to login
          </Link>
        </p>
      </div>,
    );
  }

  /* State 3: Set new password */
  if (hasSession && !done) {
    return formWrapper(
      <>
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold tracking-tight">
            Set New Password
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter your new password below.
          </p>
        </div>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="new-password">New Password</Label>
            <div className="relative">
              <Input
                id="new-password"
                type={showPassword ? "text" : "password"}
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
                className="pr-10"
              />
              <button
                type="button"
                tabIndex={-1}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {passwordTouched && passwordError && (
              <p className="text-xs text-destructive">{passwordError}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm Password</Label>
            <div className="relative">
              <Input
                id="confirm-password"
                type={showConfirm ? "text" : "password"}
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
                className="pr-10"
              />
              <button
                type="button"
                tabIndex={-1}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                onClick={() => setShowConfirm((v) => !v)}
                aria-label={showConfirm ? "Hide password" : "Show password"}
              >
                {showConfirm ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {confirmTouched && confirmError && (
              <p className="text-xs text-destructive">{confirmError}</p>
            )}
          </div>
        </div>
        <Button
          disabled={loading}
          onClick={handleReset}
          className="mt-6 w-full"
          size="lg"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Updating...
            </>
          ) : (
            "Update Password"
          )}
        </Button>
      </>,
    );
  }

  /* State 4: Done */
  return formWrapper(
    <div className="py-8 text-center">
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10">
        <CheckCircle2 className="h-7 w-7 text-emerald-500" />
      </div>
      <h3 className="text-xl font-semibold">Password Updated!</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Your password has been changed. You can now log in.
      </p>
      <Link
        href="/login"
        className={`${buttonVariants({ size: "lg" })} mt-6 inline-flex w-full justify-center`}
      >
        Go to Login
      </Link>
    </div>,
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen">
          <BrandPanel />
          <div className="flex w-full items-center justify-center md:w-1/2">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
