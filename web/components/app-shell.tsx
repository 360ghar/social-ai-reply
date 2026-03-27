"use client";

import { type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { type Project, apiRequest, isAuthError } from "@/lib/api";
import { setStoredProjectId, withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/lib/use-selected-project";

import { useAuth } from "./auth-provider";
import { ToastProvider } from "./toast";
import { NotificationBell, UsageMeter } from "./ui";

interface DashData {
  workspace_name?: string;
  projects?: Project[];
}

interface UsageData {
  metrics?: {
    keywords?: { used: number; limit: number };
    subreddits?: { used: number; limit: number };
  };
}

interface NotificationData {
  unread_count: number;
}

const NAV_SECTIONS = [
  {
    title: "Intelligence",
    items: [
      { href: "/app/dashboard", label: "Command Center", icon: "CMD", help: "Workspace overview and next actions" },
      { href: "/app/visibility", label: "AI Visibility", icon: "AI", help: "Track recommendation share across models" },
      { href: "/app/sources", label: "Source Intel", icon: "SRC", help: "See citation winners and content gaps" },
    ],
  },
  {
    title: "Engagement",
    items: [
      { href: "/app/discovery", label: "Engagement Radar", icon: "ENG", help: "Find high-fit conversations and reply opportunities" },
      { href: "/app/content", label: "Content Studio", icon: "WRT", help: "Manage replies, post drafts, and approvals" },
      { href: "/app/subreddits", label: "Communities", icon: "COM", help: "Review monitored communities and quality signals" },
    ],
  },
  {
    title: "Configure",
    items: [
      { href: "/app/brand", label: "Brand", icon: "BRD", help: "Brand profile, voice, and positioning" },
      { href: "/app/persona", label: "Audience", icon: "AUD", help: "Customer profiles and intent signals" },
      { href: "/app/prompts", label: "Templates", icon: "TPL", help: "Reply, post, and analysis prompt systems" },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/app/settings", label: "Settings", icon: "SYS", help: "Workspace controls and integrations" },
    ],
  },
];

const PATH_TITLES: Record<string, string> = {
  "/app/dashboard": "Command Center",
  "/app/visibility": "AI Visibility",
  "/app/sources": "Source Intelligence",
  "/app/discovery": "Engagement Radar",
  "/app/content": "Content Studio",
  "/app/subreddits": "Community Coverage",
  "/app/brand": "Brand Profile",
  "/app/persona": "Audience Signals",
  "/app/prompts": "Prompt Templates",
  "/app/settings": "Settings",
};

export default function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, loading: authLoading, logout } = useAuth();
  const [dash, setDash] = useState<DashData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notifCount, setNotifCount] = useState(0);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const selectedProjectId = useSelectedProjectId();

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!token) {
      router.replace("/login");
      return;
    }
    void loadShell(selectedProjectId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, token, selectedProjectId]);

  useEffect(() => {
    const projects = dash?.projects || [];
    if (!projects.length) {
      return;
    }
    if (selectedProjectId && projects.some((project) => project.id === selectedProjectId)) {
      return;
    }
    const nextProjectId = projects[0].id;
    setStoredProjectId(nextProjectId);
  }, [dash?.projects, selectedProjectId]);

  async function loadShell(projectId: number | null) {
    setLoading(true);
    try {
      const [dashRes, notifRes, usageRes] = await Promise.allSettled([
        apiRequest<DashData>(withProjectId("/v1/dashboard", projectId), {}, token),
        apiRequest<NotificationData>("/v1/notifications", {}, token),
        apiRequest<UsageData>(withProjectId("/v1/usage", projectId), {}, token),
      ]);

      if (dashRes.status === "fulfilled") {
        setDash(dashRes.value);
      }
      if (notifRes.status === "fulfilled") {
        setNotifCount(notifRes.value.unread_count || 0);
      }
      if (usageRes.status === "fulfilled") {
        setUsage(usageRes.value);
      }

      const dashFailed = dashRes.status === "rejected" && isAuthError(dashRes.reason);
      if (dashFailed) {
        logout();
        router.replace("/login");
        return;
      }
    } catch (e: any) {
      const msg = e?.message || "";
      if (msg === "Authentication required." || msg === "Invalid token.") {
        logout();
        router.replace("/login");
        return;
      }
      setError(msg || "Failed to load workspace");
    }
    setLoading(false);
  }

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  function handleProjectChange(nextValue: string) {
    const nextProjectId = Number(nextValue);
    if (!Number.isFinite(nextProjectId)) {
      return;
    }
    setStoredProjectId(nextProjectId);
    setSidebarOpen(false);
    router.refresh();
  }

  const selectedProject =
    dash?.projects?.find((project) => project.id === selectedProjectId) ??
    dash?.projects?.[0] ??
    null;

  const currentTitle = PATH_TITLES[pathname] || "Workspace";

  if (authLoading || loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
        <div style={{ textAlign: "center" }}>
          <div className="spinner spinner-lg" />
          <p className="text-muted" style={{ marginTop: 16 }}>Loading your workspace...</p>
        </div>
      </div>
    );
  }

  if (error && !dash) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
        <div className="card" style={{ textAlign: "center", maxWidth: 400 }}>
          <h3>Something went wrong</h3>
          <p className="text-muted">{error}</p>
          <button
            className="primary-button"
            onClick={() => {
              setError("");
              void loadShell(selectedProjectId);
            }}
            style={{ marginTop: 16 }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <ToastProvider>
      <div className="app-frame">
        <button
          className="mobile-menu-toggle hidden-desktop"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            zIndex: 100,
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 24,
            padding: 0,
          }}
          aria-label="Toggle navigation"
        >
          {sidebarOpen ? "x" : "="}
        </button>

        <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
          <div className="sidebar-header">
            <Link href="/app/dashboard" className="sidebar-brand" style={{ textDecoration: "none" }}>
              <div className="sidebar-badge">Community OS</div>
              <span className="sidebar-brand-title">RedditFlow</span>
            </Link>
            {dash?.workspace_name && (
              <p className="text-muted" style={{ fontSize: 12, marginTop: 6 }}>
                {dash.workspace_name}
              </p>
            )}
          </div>

          <div className="sidebar-context-card">
            <div className="sidebar-context-head">
              <div>
                <div className="sidebar-context-label">Focused Project</div>
                <div className="sidebar-context-value">{selectedProject?.name || "Create a project"}</div>
              </div>
              <span className="badge badge-info">Unlocked</span>
            </div>
            <label className="field" style={{ marginBottom: 0 }}>
              <span className="field-label" style={{ color: "rgba(255, 255, 255, 0.7)" }}>Project Scope</span>
              <select value={selectedProject?.id || ""} onChange={(event) => handleProjectChange(event.target.value)}>
                {(dash?.projects || []).map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
            <p className="sidebar-context-copy">
              AI visibility is workspace-wide. Engagement workflows are project-scoped and ready to expand beyond Reddit.
            </p>
          </div>

          <nav className="sidebar-nav">
            {NAV_SECTIONS.map((section) => (
              <div key={section.title} className="nav-section">
                <div className="nav-section-title">{section.title}</div>
                {section.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`nav-link ${pathname === item.href ? "active" : ""}`}
                    onClick={() => setSidebarOpen(false)}
                    style={{ textDecoration: "none" }}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-copy">
                      <span className="nav-label">{item.label}</span>
                      <span className="nav-help">{item.help}</span>
                    </span>
                    {item.href === "/app/visibility" && <span className="badge badge-info">Live</span>}
                  </Link>
                ))}
              </div>
            ))}
          </nav>

          {usage && (
            <div className="sidebar-footer">
              <div className="sidebar-footer-title">Workspace Use</div>
              <UsageMeter
                label="Keywords"
                used={usage.metrics?.keywords?.used || 0}
                limit={usage.metrics?.keywords?.limit || 10}
              />
              <UsageMeter
                label="Communities"
                used={usage.metrics?.subreddits?.used || 0}
                limit={usage.metrics?.subreddits?.limit || 5}
              />
            </div>
          )}

          <div className="sidebar-user">
            <button
              className="ghost-button"
              onClick={handleLogout}
              style={{ width: "100%", textAlign: "left", color: "rgba(255, 255, 255, 0.72)" }}
            >
              Sign out
            </button>
          </div>
        </aside>

        <main className="app-main">
          <div className="topbar topbar-elevated">
            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Workspace Flow</div>
              <div className="topbar-title-row">
                <h1 className="topbar-title">{currentTitle}</h1>
              </div>
              <p className="topbar-copy">
                Designed for AI visibility, community discovery, and content workflows that can scale across forum, Q&A, and social patterns.
              </p>
            </div>
            <div className="topbar-actions">
              {selectedProject && (
                <div className="topbar-project-pill">
                  <span className="topbar-project-label">Project</span>
                  <strong>{selectedProject.name}</strong>
                </div>
              )}
              <NotificationBell count={notifCount} onClick={() => router.push("/app/settings")} />
            </div>
          </div>
          <div className="app-content">{children}</div>
        </main>
      </div>
    </ToastProvider>
  );
}
