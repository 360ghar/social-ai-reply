"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button, Spinner } from "@/components/ui";
import { ToastProvider, useToast } from "@/components/toast";
import { forgotPassword, resetPassword } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { PasswordInput } from "@/components/password-input";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function ResetPasswordContent() {
  const toast = useToast();
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
      const { data: { session } } = await supabase.auth.getSession();
      if (session) setHasSession(true);
      setChecking(false);
    }
    checkSession();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (event === "PASSWORD_RECOVERY" && session) {
          setHasSession(true);
          setChecking(false);
        }
      }
    );

    return () => { subscription.unsubscribe(); };
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
      toast.success("Reset link sent!", "Check your email for the password reset link.");
    } catch (e: any) {
      toast.error("Could not send reset email", e.message);
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
      toast.success("Password updated!", "You can now log in with your new password.");
    } catch (e: any) {
      toast.error("Reset failed", e.message);
    }
    setLoading(false);
  }

  if (checking) {
    return (
      <div className="auth-shell">
        <div className="auth-card" style={{ display: "flex", justifyContent: "center", padding: 32 }}>
          <Spinner />
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h2 style={{ marginBottom: 8 }}>
          {hasSession ? "Set New Password" : "Reset Password"}
        </h2>

        {!hasSession && !sent && (
          <>
            <p className="text-muted" style={{ marginBottom: 20 }}>Enter your email and we&apos;ll send you a reset link.</p>
            <div className={`field ${emailTouched && emailError ? "has-error" : ""}`}>
              <label className="field-label">Email</label>
              <input
                ref={emailRef}
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); if (emailTouched) setEmailError(validateEmail(e.target.value)); }}
                onBlur={() => { setEmailTouched(true); setEmailError(validateEmail(email)); }}
                placeholder="you@example.com"
              />
              {emailTouched && emailError && <p className="field-error">{emailError}</p>}
            </div>
            <Button loading={loading} onClick={handleRequest} disabled={emailTouched && !!emailError} style={{ width: "100%" }}>Send Reset Link</Button>
            <p style={{ marginTop: 16, textAlign: "center" }}>
              <Link href="/login" className="text-muted">Back to login</Link>
            </p>
          </>
        )}

        {!hasSession && sent && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#x1f4e7;</div>
            <h3>Check Your Email</h3>
            <p className="text-muted">We sent a password reset link to <strong>{email}</strong>.</p>
            <p style={{ marginTop: 16 }}>
              <Link href="/login" className="text-muted">Back to login</Link>
            </p>
          </div>
        )}

        {hasSession && !done && (
          <>
            <p className="text-muted" style={{ marginBottom: 20 }}>Enter your new password below.</p>
            <div className={`field ${passwordTouched && passwordError ? "has-error" : ""}`}>
              <label className="field-label">New Password</label>
              <PasswordInput
                value={password}
                onChange={(e) => {
                  const v = (e.target as HTMLInputElement).value;
                  setPassword(v);
                  if (passwordTouched) setPasswordError(validatePassword(v));
                  if (confirmTouched && confirm) setConfirmError(confirm !== v ? "Passwords do not match." : "");
                }}
                onBlur={() => { setPasswordTouched(true); setPasswordError(validatePassword(password)); }}
                placeholder="Min 8 characters"
                autoComplete="new-password"
                showStrength
                error={passwordTouched ? passwordError : undefined}
              />
            </div>
            <div className={`field ${confirmTouched && confirmError ? "has-error" : ""}`}>
              <label className="field-label">Confirm Password</label>
              <PasswordInput
                value={confirm}
                onChange={(e) => { const v = (e.target as HTMLInputElement).value; setConfirm(v); if (confirmTouched) setConfirmError(v !== password ? "Passwords do not match." : ""); }}
                onBlur={() => { setConfirmTouched(true); setConfirmError(validateConfirm(confirm)); }}
                placeholder="Type password again"
                autoComplete="new-password"
                error={confirmTouched ? confirmError : undefined}
              />
            </div>
            <Button loading={loading} onClick={handleReset} style={{ width: "100%" }}>Update Password</Button>
          </>
        )}

        {hasSession && done && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#x2705;</div>
            <h3>Password Updated!</h3>
            <p className="text-muted">Your password has been changed. You can now log in.</p>
            <Link href="/login" className="primary-button" style={{ display: "inline-block", marginTop: 16, textDecoration: "none" }}>Go to Login</Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <ToastProvider>
      <Suspense fallback={<div className="auth-shell"><div className="auth-card" style={{ display: "flex", justifyContent: "center", padding: 32 }}><Spinner /></div></div>}>
        <ResetPasswordContent />
      </Suspense>
    </ToastProvider>
  );
}
