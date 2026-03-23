"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { ToastProvider, useToast } from "@/components/toast";
import { Button } from "@/components/ui";

function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) {
      toast.warning("Please enter your email and password.");
      return;
    }
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
      toast.success("Welcome back!");
      router.push("/app/dashboard");
    } catch (e: any) {
      toast.error("Login failed", e.message || "Invalid email or password.");
    }
    setLoading(false);
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h2 style={{ color: "var(--accent)", fontWeight: 800, fontSize: 24, marginBottom: 4 }}>
            RedditFlow
          </h2>
          <p className="text-muted">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="field-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </div>
          <div className="field">
            <div className="flex justify-between items-center">
              <label className="field-label" htmlFor="password">
                Password
              </label>
              <a href="/reset-password" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}>
                Forgot password?
              </a>
            </div>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              autoComplete="current-password"
              required
            />
          </div>
          <Button type="submit" loading={loading} style={{ width: "100%", marginTop: 8 }}>
            Sign In
          </Button>
        </form>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 13 }}>
          Need an account?{" "}
          <a href="/register" style={{ color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>
            Sign up free
          </a>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <ToastProvider>
      <LoginForm />
    </ToastProvider>
  );
}
