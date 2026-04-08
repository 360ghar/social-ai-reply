"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { ToastProvider, useToast } from "@/components/toast";
import { Button } from "@/components/ui";
import { PasswordInput } from "@/components/password-input";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function LoginForm() {
  const router = useRouter();
  const { login, loginWithGoogle } = useAuth();
  const toast = useToast();
  const emailRef = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});

  useEffect(() => { emailRef.current?.focus(); }, []);

  function validateEmail(v: string): string {
    if (!v.trim()) return "Email is required.";
    if (!EMAIL_RE.test(v.trim())) return "Please enter a valid email.";
    return "";
  }

  function validatePassword(v: string): string {
    if (!v) return "Password is required.";
    return "";
  }

  function handleBlur(field: "email" | "password") {
    setTouched((t) => ({ ...t, [field]: true }));
    if (field === "email") setErrors((e) => ({ ...e, email: validateEmail(email) }));
    if (field === "password") setErrors((e) => ({ ...e, password: validatePassword(password) }));
  }

  const isValid = !validateEmail(email) && !validatePassword(password);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const emailErr = validateEmail(email);
    const passErr = validatePassword(password);
    if (emailErr || passErr) {
      setErrors({ email: emailErr, password: passErr });
      setTouched({ email: true, password: true });
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

  async function handleGoogle() {
    setGoogleLoading(true);
    try {
      await loginWithGoogle();
    } catch (e: any) {
      toast.error("Google sign-in failed", e.message);
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
          <p className="text-muted">Sign in to your account</p>
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
          <div className={`field ${touched.email && errors.email ? "has-error" : ""}`}>
            <label className="field-label" htmlFor="email">
              Email
            </label>
            <input
              ref={emailRef}
              id="email"
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); if (touched.email) setErrors((err) => ({ ...err, email: validateEmail(e.target.value) })); }}
              onBlur={() => handleBlur("email")}
              placeholder="you@example.com"
              autoComplete="email"
            />
            {touched.email && errors.email && <p className="field-error">{errors.email}</p>}
          </div>
          <div className={`field ${touched.password && errors.password ? "has-error" : ""}`}>
            <div className="flex justify-between items-center">
              <label className="field-label" htmlFor="password">
                Password
              </label>
              <Link href="/reset-password" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}>
                Forgot password?
              </Link>
            </div>
            <PasswordInput
              id="password"
              value={password}
              onChange={(e) => { setPassword((e.target as HTMLInputElement).value); if (touched.password) setErrors((err) => ({ ...err, password: validatePassword((e.target as HTMLInputElement).value) })); }}
              onBlur={() => handleBlur("password")}
              placeholder="Your password"
              autoComplete="current-password"
              error={touched.password ? errors.password : undefined}
            />
          </div>
          <Button type="submit" loading={loading} disabled={!isValid && (touched.email || false) && (touched.password || false)} style={{ width: "100%", marginTop: 8 }}>
            Sign In
          </Button>
        </form>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 13 }}>
          Need an account?{" "}
          <Link href="/register" style={{ color: "var(--accent)", fontWeight: 600, textDecoration: "none" }}>
            Sign up free
          </Link>
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
