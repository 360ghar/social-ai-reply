"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const validators: Record<string, (v: string) => string> = {
  fullName: (v) =>
    !v.trim()
      ? "Full name is required."
      : v.trim().length < 2
        ? "Must be at least 2 characters."
        : "",
  email: (v) =>
    !v.trim()
      ? "Email is required."
      : !EMAIL_RE.test(v.trim())
        ? "Please enter a valid email."
        : "",
  password: (v) =>
    !v
      ? "Password is required."
      : v.length < 8
        ? "Must be at least 8 characters."
        : "",
  workspace: (v) =>
    !v.trim()
      ? "Workspace name is required."
      : v.trim().length < 2
        ? "Must be at least 2 characters."
        : "",
};

function RegisterForm() {
  const router = useRouter();
  const { register, loginWithGoogle } = useAuth();
  const { success, error } = useToast();
  const nameRef = useRef<HTMLInputElement>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  function handleBlur(field: string) {
    setTouched((t) => ({ ...t, [field]: true }));
    const value = ({ fullName, email, password, workspace } as Record<
      string,
      string
    >)[field] ?? "";
    setErrors((e) => ({ ...e, [field]: validators[field](value) }));
  }

  function validate(field: string, value: string) {
    if (touched[field])
      setErrors((e) => ({ ...e, [field]: validators[field](value) }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const values: Record<string, string> = {
      fullName,
      email,
      password,
      workspace,
    };
    const newErrors: Record<string, string> = {};
    for (const [field, fn] of Object.entries(validators)) {
      newErrors[field] = fn(values[field] ?? "");
    }
    setErrors(newErrors);
    setTouched({
      fullName: true,
      email: true,
      password: true,
      workspace: true,
    });
    if (Object.values(newErrors).some(Boolean)) return;

    setLoading(true);
    try {
      await register({
        fullName: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
        workspaceName: workspace.trim(),
      });
      success("Account created!", "Let's set up your brand.");
      router.push("/app/dashboard");
    } catch (e: any) {
      error("Registration failed", e.message || "Could not create account.");
    }
    setLoading(false);
  }

  async function handleGoogle() {
    setGoogleLoading(true);
    try {
      await loginWithGoogle();
    } catch (e: any) {
      error("Google sign-up failed", e.message);
      setGoogleLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md rounded-xl border bg-card p-8 shadow-sm">
        <div className="mb-8 text-center">
          <h2 className="mb-1 text-2xl font-extrabold text-primary">
            RedditFlow
          </h2>
          <p className="text-muted-foreground">Create your free account</p>
        </div>

        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={handleGoogle}
          disabled={googleLoading || loading}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          {googleLoading ? "Redirecting..." : "Continue with Google"}
        </Button>

        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">or</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="name">Full Name</Label>
            <Input
              ref={nameRef}
              id="name"
              type="text"
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                validate("fullName", e.target.value);
              }}
              onBlur={() => handleBlur("fullName")}
              placeholder="John Smith"
              aria-invalid={touched.fullName && !!errors.fullName}
            />
            {touched.fullName && errors.fullName && (
              <p className="text-xs text-destructive">{errors.fullName}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                validate("email", e.target.value);
              }}
              onBlur={() => handleBlur("email")}
              placeholder="you@example.com"
              autoComplete="email"
              aria-invalid={touched.email && !!errors.email}
            />
            {touched.email && errors.email && (
              <p className="text-xs text-destructive">{errors.email}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                validate("password", e.target.value);
              }}
              onBlur={() => handleBlur("password")}
              placeholder="Min 8 characters"
              autoComplete="new-password"
              aria-invalid={touched.password && !!errors.password}
            />
            {touched.password && errors.password ? (
              <p className="text-xs text-destructive">{errors.password}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                Must be at least 8 characters
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="workspace">Workspace Name</Label>
            <Input
              id="workspace"
              type="text"
              value={workspace}
              onChange={(e) => {
                setWorkspace(e.target.value);
                validate("workspace", e.target.value);
              }}
              onBlur={() => handleBlur("workspace")}
              placeholder="Your company name"
              aria-invalid={touched.workspace && !!errors.workspace}
            />
            {touched.workspace && errors.workspace ? (
              <p className="text-xs text-destructive">{errors.workspace}</p>
            ) : (
              <p className="text-xs text-muted-foreground">
                This is your team&apos;s shared workspace
              </p>
            )}
          </div>
          <Button type="submit" disabled={loading} className="mt-2 w-full">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Create Account
          </Button>
        </form>

        <p className="mt-6 text-center text-[13px]">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-semibold text-primary hover:underline"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return <RegisterForm />;
}
