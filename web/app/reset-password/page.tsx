"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui";
import { ToastProvider, useToast } from "@/components/toast";
import { forgotPassword, resetPassword } from "@/lib/api";
import { supabase } from "@/lib/supabase";

function ResetPasswordContent() {
  const params = useSearchParams();
  const toast = useToast();

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
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setHasSession(true);
      }
      setChecking(false);
    }
    checkSession();

    // Listen for auth events — Supabase fires PASSWORD_RECOVERY when user clicks reset link
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

  async function handleRequest() {
    if (!email.trim()) { toast.warning("Please enter your email."); return; }
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
    if (password.length < 8) { toast.warning("Password must be at least 8 characters."); return; }
    if (password !== confirm) { toast.warning("Passwords do not match."); return; }
    setLoading(true);
    try {
      await resetPassword("", password);
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
        <div className="auth-card">Loading...</div>
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
            <div className="field">
              <label className="field-label">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" />
            </div>
            <Button loading={loading} onClick={handleRequest} style={{ width: "100%" }}>Send Reset Link</Button>
            <p style={{ marginTop: 16, textAlign: "center" }}>
              <a href="/login" className="text-muted">Back to login</a>
            </p>
          </>
        )}

        {!hasSession && sent && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#x1f4e7;</div>
            <h3>Check Your Email</h3>
            <p className="text-muted">We sent a password reset link to <strong>{email}</strong>.</p>
            <p style={{ marginTop: 16 }}>
              <a href="/login" className="text-muted">Back to login</a>
            </p>
          </div>
        )}

        {hasSession && !done && (
          <>
            <p className="text-muted" style={{ marginBottom: 20 }}>Enter your new password below.</p>
            <div className="field">
              <label className="field-label">New Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Min 8 characters" />
            </div>
            <div className="field">
              <label className="field-label">Confirm Password</label>
              <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Type password again" />
            </div>
            <Button loading={loading} onClick={handleReset} style={{ width: "100%" }}>Update Password</Button>
          </>
        )}

        {hasSession && done && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#x2705;</div>
            <h3>Password Updated!</h3>
            <p className="text-muted">Your password has been changed. You can now log in.</p>
            <a href="/login" className="primary-button" style={{ display: "inline-block", marginTop: 16, textDecoration: "none" }}>Go to Login</a>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <ToastProvider>
      <Suspense fallback={<div className="auth-shell"><div className="auth-card">Loading...</div></div>}>
        <ResetPasswordContent />
      </Suspense>
    </ToastProvider>
  );
}
