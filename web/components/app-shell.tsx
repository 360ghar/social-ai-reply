"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiRequest, isAuthError, type Dashboard } from "../lib/api";
import { formatPlan, formatStatus } from "../lib/format";
import { resolveProjectId, setStoredProjectId } from "../lib/project";
import { useAuth } from "./auth-provider";

const primaryNav = [
  { href: "/app/dashboard", label: "Home", help: "See your next step" },
  { href: "/app/brand", label: "Your product", help: "Tell us what you sell" },
  { href: "/app/persona", label: "Customers", help: "Describe who you want to reach" },
  { href: "/app/discovery", label: "Find posts", help: "Search Reddit and draft replies" },
  { href: "/app/subreddits", label: "Communities", help: "Review subreddit fit and rules" }
];

const secondaryNav = [
  { href: "/app/prompts", label: "Writing style", help: "Optional AI wording rules" },
  { href: "/app/settings", label: "Connections", help: "Optional webhooks and saved keys" },
  { href: "/app/subscription", label: "Plan", help: "Usage and pricing" }
];

const navItems = [...primaryNav, ...secondaryNav];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { token, user, workspace, logout, loading } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) {
      return;
    }
    if (!token) {
      router.replace("/login");
      return;
    }
    let ignore = false;
    setDashboardError(null);
    apiRequest<Dashboard>("/v1/dashboard", {}, token)
      .then((payload) => {
        if (ignore) {
          return;
        }
        setDashboard(payload);
        const selected = resolveProjectId(payload.projects);
        if (selected) {
          setStoredProjectId(selected);
        }
      })
      .catch((err) => {
        if (ignore) {
          return;
        }
        if (isAuthError(err)) {
          logout();
          router.replace("/login");
          return;
        }
        setDashboardError(err instanceof Error ? err.message : "Could not load your workspace.");
      });
    return () => {
      ignore = true;
    };
  }, [loading, router, token]);

  if (loading) {
    return (
      <main className="app-main">
        <section className="card">
          <div className="empty-state">Loading your workspace...</div>
        </section>
      </main>
    );
  }

  if (!token) {
    return null;
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="eyebrow">RedditFlow</div>
          <div className="sidebar-title">Find Reddit posts where your product can genuinely help.</div>
          <p className="sidebar-subtext">
            Start with your product, add customer types, create search words, find communities, then draft replies.
          </p>
        </div>
        <div className="nav-group">
          <div className="nav-section-title">Start here</div>
          <nav className="nav-list">
            {primaryNav.map((item) => (
              <Link key={item.href} href={item.href} className={pathname === item.href ? "nav-link active" : "nav-link"}>
                <span>{item.label}</span>
                <small className="nav-help">{item.help}</small>
              </Link>
            ))}
          </nav>
        </div>
        <div className="nav-group">
          <div className="nav-section-title">Optional</div>
          <nav className="nav-list">
            {secondaryNav.map((item) => (
              <Link key={item.href} href={item.href} className={pathname === item.href ? "nav-link active" : "nav-link"}>
                <span>{item.label}</span>
                <small className="nav-help">{item.help}</small>
              </Link>
            ))}
          </nav>
        </div>
        <div className="sidebar-footer">
          <div>
            <div className="meta-label">Team space</div>
            <div>{workspace?.name ?? "Loading..."}</div>
          </div>
          <div>
            <div className="meta-label">Signed in</div>
            <div>{user?.email ?? "..."}</div>
          </div>
          {dashboard?.projects.length ? (
            <label className="field">
              <span>Current business</span>
              <select
                value={String(resolveProjectId(dashboard.projects) ?? "")}
                onChange={(event) => {
                  setStoredProjectId(Number(event.target.value));
                  window.location.reload();
                }}
              >
                {dashboard.projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button className="ghost-button" onClick={() => { logout(); router.push("/login"); }}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="app-main">
        <div className="app-topbar">
          <div>
            <div className="eyebrow">Simple workflow</div>
            <h2>{navItems.find((item) => item.href === pathname)?.label ?? "Workspace"}</h2>
          </div>
          <div className="status-pill">
            <span>{formatPlan(dashboard?.subscription.plan_code)}</span>
            <span>{formatStatus(dashboard?.subscription.status)}</span>
          </div>
        </div>
        {dashboardError ? (
          <section className="card">
            <div className="notice">{dashboardError}</div>
          </section>
        ) : null}
        {children}
      </main>
    </div>
  );
}
