"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { ToastProvider, useToast } from "@/components/toast";
import { Button } from "@/components/ui";

function RegisterForm() {
  const router = useRouter();
  const { register } = useAuth();
  const toast = useToast();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName.trim() || !email.trim() || !password || !workspace.trim()) {
      toast.warning("All fields are required.");
      return;
    }
    if (password.length < 8) {
      toast.warning("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await register({
        fullName: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
        workspaceName: workspace.trim(),
      });
      toast.success("Account created!", "Let's set up your brand.");
      router.push("/app/dashboard");
    } catch (e: any) {
      toast.error("Registration failed", e.message || "Could not create account.");
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
          <p className="text-muted">Create your free account</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="field-label" htmlFor="name">
              Full Name
            </label>
            <input
              id="name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="John Smith"
              required
            />
          </div>
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
              required
            />
          </div>
          <div className="field">
            <label className="field-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min 8 characters"
              required
              minLength={8}
            />
            <p className="field-help">Must be at least 8 characters</p>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="workspace">
              Workspace Name
            </label>
            <input
              id="workspace"
              type="text"
              value={workspace}
              onChange={(e) => setWorkspace(e.target.value)}
              placeholder="Your company name"
              required
            />
            <p className="field-help">This is your team's shared workspace</p>
          </div>
          <Button type="submit" loading={loading} style={{ width: "100%", marginTop: 8 }}>
            Create Account
          </Button>
        </form>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 13 }}>
          Already have an account?{" "}
          <a href="/login" style={{ color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <ToastProvider>
      <RegisterForm />
    </ToastProvider>
  );
}
