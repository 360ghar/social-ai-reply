"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui";
import { useToast } from "@/components/toast";
import { forgotPassword, resetPassword } from "@/lib/api";

export default function ResetPasswordPage() {
  const params = useSearchParams();
  const token = params.get("token");
  const toast = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [done, setDone] = useState(false);

  async function handleRequest() {
    if (!email.trim()) { toast.warning("Please enter your email."); return; }
    setLoading(true);
    try {
      await forgotPassword(email.trim());
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
      await resetPassword(token!, password);
      setDone(true);
      toast.success("Password updated!", "You can now log in with your new password.");
    } catch (e: any) {
      toast.error("Reset failed", e.message);
    }
    setLoading(false);
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h2 style={{ marginBottom: 8 }}>
          {token ? "Set New Password" : "Reset Password"}
        </h2>

        {!token && !sent && (
          <>
            <p className="text-muted" style={{ marginBottom: 20 }}>Enter your email and we'll send you a reset link.</p>
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

        {!token && sent && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📧</div>
            <h3>Check Your Email</h3>
            <p className="text-muted">We sent a password reset link to <strong>{email}</strong>. It expires in 1 hour.</p>
            <p style={{ marginTop: 16 }}>
              <a href="/login" className="text-muted">Back to login</a>
            </p>
          </div>
        )}

        {token && !done && (
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

        {token && done && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
            <h3>Password Updated!</h3>
            <p className="text-muted">Your password has been changed. You can now log in.</p>
            <a href="/login" className="primary-button" style={{ display: "inline-block", marginTop: 16, textDecoration: "none" }}>Go to Login</a>
          </div>
        )}
      </div>
    </div>
  );
}
