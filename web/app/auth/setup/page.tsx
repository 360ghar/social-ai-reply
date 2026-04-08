"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { supabase } from "@/lib/supabase";
import { ToastProvider, useToast } from "@/components/toast";
import { Button } from "@/components/ui";

function SetupForm() {
  const router = useRouter();
  const { completeOAuthSetup } = useAuth();
  const toast = useToast();
  const [workspace, setWorkspace] = useState("");
  const [loading, setLoading] = useState(false);
  const [userInfo, setUserInfo] = useState<{ email: string; name: string }>({ email: "", name: "" });
  const [fieldError, setFieldError] = useState("");

  useEffect(() => {
    async function loadUser() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.replace("/login");
        return;
      }
      const meta = session.user?.user_metadata ?? {};
      setUserInfo({
        email: session.user?.email ?? "",
        name: meta.full_name ?? meta.name ?? "",
      });
    }
    loadUser();
  }, [router]);

  function validateWorkspace(value: string): string {
    if (!value.trim()) return "Workspace name is required.";
    if (value.trim().length < 2) return "Must be at least 2 characters.";
    return "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validateWorkspace(workspace);
    if (err) {
      setFieldError(err);
      return;
    }
    setLoading(true);
    try {
      await completeOAuthSetup(workspace.trim());
      toast.success("Account created!", "Your workspace is ready.");
      router.push("/app/dashboard");
    } catch (e: any) {
      toast.error("Setup failed", e.message || "Could not create workspace.");
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
          <p className="text-muted">One more step to get started</p>
        </div>

        {userInfo.email && (
          <div style={{ background: "var(--surface)", borderRadius: "var(--radius-md)", padding: "12px 16px", marginBottom: 24, fontSize: 13 }}>
            <div style={{ fontWeight: 600 }}>{userInfo.name || "Welcome!"}</div>
            <div className="text-muted">{userInfo.email}</div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className={`field ${fieldError ? "has-error" : ""}`}>
            <label className="field-label" htmlFor="workspace">
              Workspace Name
            </label>
            <input
              id="workspace"
              type="text"
              value={workspace}
              onChange={(e) => { setWorkspace(e.target.value); setFieldError(""); }}
              onBlur={() => setFieldError(validateWorkspace(workspace))}
              placeholder="Your company name"
              autoFocus
              required
            />
            {fieldError && <p className="field-error">{fieldError}</p>}
            <p className="field-help">This is your team's shared workspace</p>
          </div>
          <Button type="submit" loading={loading} style={{ width: "100%", marginTop: 8 }}>
            Create Workspace
          </Button>
        </form>
      </div>
    </div>
  );
}

export default function AuthSetupPage() {
  return (
    <ToastProvider>
      <SetupForm />
    </ToastProvider>
  );
}
