"use client";
import { useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "./auth-provider";
import { ToastProvider } from "./toast";
import { NotificationBell, UsageMeter } from "./ui";
import { apiRequest } from "@/lib/api";

interface DashData {
  workspace_name?: string;
  plan_code?: string;
  plan_status?: string;
  projects?: any[];
}

interface UsageData {
  plan?: string;
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
    title: "Core",
    items: [
      { href: "/app/dashboard", label: "Dashboard", icon: "📊", help: "Overview and quick actions" },
      { href: "/app/visibility", label: "AI Visibility", icon: "👁️", help: "Track brand in AI models" },
      { href: "/app/sources", label: "Source Intel", icon: "🔗", help: "Citation and domain analysis" },
      { href: "/app/discovery", label: "Opportunities", icon: "🔍", help: "Find and score threads" },
      { href: "/app/content", label: "Content Studio", icon: "✍️", help: "Drafts and approvals" },
    ],
  },
  {
    title: "Setup",
    items: [
      { href: "/app/brand", label: "Brand", icon: "🏢", help: "Brand profile and voice" },
      { href: "/app/persona", label: "Audience", icon: "👥", help: "Personas and keywords" },
      { href: "/app/subreddits", label: "Communities", icon: "💬", help: "Monitored subreddits" },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/app/prompts", label: "Templates", icon: "📋", help: "AI prompt templates" },
      { href: "/app/settings", label: "Settings", icon: "⚙️", help: "Workspace and team" },
      { href: "/app/subscription", label: "Billing", icon: "💳", help: "Plan and usage" },
    ],
  },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { token, logout } = useAuth();
  const [dash, setDash] = useState<DashData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notifCount, setNotifCount] = useState(0);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!token) {
      router.replace("/login");
      return;
    }
    loadShell();
  }, [token]);

  async function loadShell() {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [dashRes, notifRes, usageRes] = await Promise.allSettled([
        apiRequest<DashData>("/v1/dashboard", {}, token),
        apiRequest<NotificationData>("/v1/notifications", {}, token),
        apiRequest<UsageData>("/v1/usage", {}, token),
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
    } catch (e: any) {
      if (
        e?.message?.includes("401") ||
        e?.message?.includes("Not authenticated") ||
        e?.message?.includes("Authentication required")
      ) {
        logout();
        router.replace("/login");
        return;
      }
      setError(e?.message || "Failed to load workspace");
    }
    setLoading(false);
  }

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  if (loading) {
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
              loadShell();
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
        {/* Mobile menu toggle */}
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
        >
          {sidebarOpen ? "✕" : "☰"}
        </button>

        <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
          <div className="sidebar-header">
            <a href="/app/dashboard" className="sidebar-brand" style={{ textDecoration: "none" }}>
              <span style={{ fontSize: 20, fontWeight: 800, color: "var(--accent)" }}>RedditFlow</span>
            </a>
            {dash?.workspace_name && (
              <p className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>{dash.workspace_name}</p>
            )}
          </div>

          <nav className="sidebar-nav">
            {NAV_SECTIONS.map((section) => (
              <div key={section.title} className="nav-section">
                <div className="nav-section-title">{section.title}</div>
                {section.items.map((item) => (
                  <a
                    key={item.href}
                    href={item.href}
                    className={`nav-link ${pathname === item.href ? "active" : ""}`}
                    onClick={() => setSidebarOpen(false)}
                    style={{ textDecoration: "none" }}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                    {item.href === "/app/visibility" && (
                      <span className="badge badge-info" style={{ marginLeft: "auto", fontSize: 10 }}>
                        NEW
                      </span>
                    )}
                  </a>
                ))}
              </div>
            ))}
          </nav>

          {/* Usage footer */}
          {usage && (
            <div className="sidebar-footer">
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
              <div style={{ marginTop: 8 }}>
                <span className="badge" style={{ textTransform: "capitalize" }}>
                  {usage.plan || "free"} plan
                </span>
              </div>
            </div>
          )}

          <div className="sidebar-user">
            <button
              className="ghost-button"
              onClick={handleLogout}
              style={{ width: "100%", textAlign: "left", color: "var(--muted)" }}
            >
              Sign out
            </button>
          </div>
        </aside>

        <main className="app-main">
          <div className="topbar">
            <div className="flex items-center gap-md">
              <span className="badge">{dash?.plan_code || "free"}</span>
              {dash?.plan_status && (
                <span className="text-muted" style={{ fontSize: 12 }}>
                  {dash.plan_status}
                </span>
              )}
            </div>
            <div className="flex items-center gap-md">
              <NotificationBell count={notifCount} onClick={() => router.push("/app/settings")} />
            </div>
          </div>
          <div className="app-content">{children}</div>
        </main>
      </div>
    </ToastProvider>
  );
}
