"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { ToastProvider, useToast } from "@/components/toast";
import { Button } from "@/components/ui";
import { PasswordInput } from "@/components/password-input";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function RegisterForm() {
  const router = useRouter();
  const { register, loginWithGoogle } = useAuth();
  const toast = useToast();
  const nameRef = useRef<HTMLInputElement>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspace, setWorkspace] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  useEffect(() => { nameRef.current?.focus(); }, []);

  const validators: Record<string, (v: string) => string> = {
    fullName: (v) => !v.trim() ? "Full name is required." : v.trim().length < 2 ? "Must be at least 2 characters." : "",
    email: (v) => !v.trim() ? "Email is required." : !EMAIL_RE.test(v.trim()) ? "Please enter a valid email." : "",
    password: (v) => !v ? "Password is required." : v.length < 8 ? "Must be at least 8 characters." : "",
    workspace: (v) => !v.trim() ? "Workspace name is required." : v.trim().length < 2 ? "Must be at least 2 characters." : "",
  };

  function handleBlur(field: string) {
    setTouched((t) => ({ ...t, [field]: true }));
    const value = { fullName, email, password, workspace }[field] ?? "";
    setErrors((e) => ({ ...e, [field]: validators[field](value) }));
  }

  function validate(field: string, value: string) {
    if (touched[field]) setErrors((e) => ({ ...e, [field]: validators[field](value) }));
  }

  const isValid = !validators.fullName(fullName) && !validators.email(email) && !validators.password(password) && !validators.workspace(workspace);
  const allTouched = touched.fullName && touched.email && touched.password && touched.workspace;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const newErrors: Record<string, string> = {};
    for (const [field, fn] of Object.entries(validators)) {
      newErrors[field] = fn({ fullName, email, password, workspace }[field] ?? "");
    }
    setErrors(newErrors);
    setTouched({ fullName: true, email: true, password: true, workspace: true });
    if (Object.values(newErrors).some(Boolean)) return;

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

  async function handleGoogle() {
    setGoogleLoading(true);
    try {
      await loginWithGoogle();
    } catch (e: any) {
      toast.error("Google sign-up failed", e.message);
      setGoogleLoading(false);
    }
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

        <button
          type="button"
          className="google-button"
          onClick={handleGoogle}
          disabled={googleLoading || loading}
        >
          <svg width="18" height="18" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          {googleLoading ? "Redirecting..." : "Continue with Google"}
        </button>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <form onSubmit={handleSubmit}>
          <div className={`field ${touched.fullName && errors.fullName ? "has-error" : ""}`}>
            <label className="field-label" htmlFor="name">
              Full Name
            </label>
            <input
              ref={nameRef}
              id="name"
              type="text"
              value={fullName}
              onChange={(e) => { setFullName(e.target.value); validate("fullName", e.target.value); }}
              onBlur={() => handleBlur("fullName")}
              placeholder="John Smith"
            />
            {touched.fullName && errors.fullName && <p className="field-error">{errors.fullName}</p>}
          </div>
          <div className={`field ${touched.email && errors.email ? "has-error" : ""}`}>
            <label className="field-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); validate("email", e.target.value); }}
              onBlur={() => handleBlur("email")}
              placeholder="you@example.com"
            />
            {touched.email && errors.email && <p className="field-error">{errors.email}</p>}
          </div>
          <div className={`field ${touched.password && errors.password ? "has-error" : ""}`}>
            <label className="field-label" htmlFor="password">
              Password
            </label>
            <PasswordInput
              id="password"
              value={password}
              onChange={(e) => { setPassword((e.target as HTMLInputElement).value); validate("password", (e.target as HTMLInputElement).value); }}
              onBlur={() => handleBlur("password")}
              placeholder="Min 8 characters"
              autoComplete="new-password"
              showStrength
              error={touched.password ? errors.password : undefined}
            />
          </div>
          <div className={`field ${touched.workspace && errors.workspace ? "has-error" : ""}`}>
            <label className="field-label" htmlFor="workspace">
              Workspace Name
            </label>
            <input
              id="workspace"
              type="text"
              value={workspace}
              onChange={(e) => { setWorkspace(e.target.value); validate("workspace", e.target.value); }}
              onBlur={() => handleBlur("workspace")}
              placeholder="Your company name"
            />
            {touched.workspace && errors.workspace && <p className="field-error">{errors.workspace}</p>}
            {!(touched.workspace && errors.workspace) && <p className="field-help">This is your team's shared workspace</p>}
          </div>
          <Button type="submit" loading={loading} disabled={allTouched && !isValid} style={{ width: "100%", marginTop: 8 }}>
            Create Account
          </Button>
        </form>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 13 }}>
          Already have an account?{" "}
          <Link href="/login" style={{ color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>
            Sign in
          </Link>
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
