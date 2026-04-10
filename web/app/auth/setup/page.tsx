"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { supabase } from "@/lib/supabase";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function SetupForm() {
  const router = useRouter();
  const { completeOAuthSetup } = useAuth();
  const { success, error } = useToast();
  const [workspace, setWorkspace] = useState("");
  const [loading, setLoading] = useState(false);
  const [userInfo, setUserInfo] = useState<{ email: string; name: string }>({
    email: "",
    name: "",
  });
  const [fieldError, setFieldError] = useState("");

  useEffect(() => {
    async function loadUser() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.replace("/login");
        return;
      }
      const meta = (session.user?.user_metadata ?? {}) as Record<string, unknown>;
      setUserInfo({
        email: session.user?.email ?? "",
        name:
          (meta.full_name as string | undefined) ??
          (meta.name as string | undefined) ??
          "",
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
      success("Account created!", "Your workspace is ready.");
      router.push("/app/dashboard");
    } catch (e: any) {
      error("Setup failed", e.message || "Could not create workspace.");
    }
    setLoading(false);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md rounded-xl border bg-card p-8 shadow-sm">
        <div className="mb-8 text-center">
          <h2 className="mb-1 text-2xl font-extrabold text-primary">
            RedditFlow
          </h2>
          <p className="text-muted-foreground">One more step to get started</p>
        </div>

        {userInfo.email && (
          <div className="mb-6 rounded-md bg-muted px-4 py-3 text-[13px]">
            <div className="font-semibold">{userInfo.name || "Welcome!"}</div>
            <div className="text-muted-foreground">{userInfo.email}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="workspace">Workspace Name</Label>
            <Input
              id="workspace"
              type="text"
              value={workspace}
              onChange={(e) => {
                setWorkspace(e.target.value);
                setFieldError("");
              }}
              onBlur={() => setFieldError(validateWorkspace(workspace))}
              placeholder="Your company name"
              autoFocus
              required
              aria-invalid={!!fieldError}
            />
            {fieldError ? (
              <p className="text-xs text-destructive">{fieldError}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                This is your team&apos;s shared workspace
              </p>
            )}
          </div>
          <Button type="submit" disabled={loading} className="mt-2 w-full">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Create Workspace
          </Button>
        </form>
      </div>
    </div>
  );
}

export default function AuthSetupPage() {
  return <SetupForm />;
}
