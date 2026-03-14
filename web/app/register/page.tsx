"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { useAuth } from "../../components/auth-provider";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await register({ fullName, workspaceName, email, password });
      router.push("/app/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create workspace.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="auth-shell">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="eyebrow">Create Account</div>
        <h2>Start using RedditFlow.</h2>
        <p>Create your team space, then add your first business inside the app.</p>
        <label className="field">
          <span>Full name</span>
          <input value={fullName} onChange={(event) => setFullName(event.target.value)} required />
        </label>
        <label className="field">
          <span>Team space name</span>
          <input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} required />
        </label>
        <label className="field">
          <span>Email</span>
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        </label>
        <label className="field">
          <span>Password</span>
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
        </label>
        {error ? <div className="notice">{error}</div> : null}
        <button className="primary-button" disabled={saving} type="submit">
          {saving ? "Creating..." : "Create account"}
        </button>
        <p>
          Already registered? <Link href="/login">Sign in</Link>.
        </p>
      </form>
    </main>
  );
}
