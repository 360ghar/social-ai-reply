"use client";

import { type ReactNode, useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { type Project, apiRequest, isAuthError } from "@/lib/api";
import { setStoredProjectId, withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/lib/use-selected-project";

import { useAuth } from "./auth-provider";
import { ToastProvider } from "./toast";
import { NotificationBell } from "./ui";

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

interface NotificationItem {
  id: number;
  title: string;
  message: string;
  icon: string;
  link?: string;
  read: boolean;
  created_at: string;
}

const NAV_SECTIONS = [
  {
    title: "OVERVIEW",
    items: [
      { href: "/app/dashboard", label: "Dashboard", icon: "D" },
      { href: "/app/auto-pipeline", label: "Auto Pipeline", icon: "A", badge: "New" },
    ],
  },
  {
    title: "MONITOR",
    items: [
      { href: "/app/visibility", label: "AI Visibility", icon: "V" },
      { href: "/app/sources", label: "Source Intel", icon: "S" },
    ],
  },
  {
    title: "ENGAGE",
    items: [
      { href: "/app/discovery", label: "Opportunity Radar", icon: "R" },
      { href: "/app/content", label: "Content Studio", icon: "C" },
      { href: "/app/subreddits", label: "Communities", icon: "U" },
    ],
  },
  {
    title: "CONFIGURE",
    items: [
      { href: "/app/brand", label: "Brand Profile", icon: "B" },
      { href: "/app/persona", label: "Personas", icon: "P" },
      { href: "/app/prompts", label: "Prompts", icon: "T" },
    ],
  },
  {
    title: "SETTINGS",
    items: [
      { href: "/app/settings", label: "Settings", icon: "G" },
    ],
  },
];

const PATH_TITLES: Record<string, string> = {
  "/app/dashboard": "Command Center",
  "/app/auto-pipeline": "Auto Pipeline",
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
  const [initialLoad, setInitialLoad] = useState(true);
  const [error, setError] = useState("");
  const [notifCount, setNotifCount] = useState(0);
  const [_usage, _setUsage] = useState<UsageData | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const selectedProjectId = useSelectedProjectId();
  const [notifPanelOpen, setNotifPanelOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notifLoading, setNotifLoading] = useState(false);
  const notifPanelRef = useRef<HTMLDivElement>(null);

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
    if (!token) return;
    void loadNotifications();
    const interval = setInterval(() => {
      void loadNotifications();
    }, 30000);
    return () => clearInterval(interval);
  }, [token]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifPanelRef.current && !notifPanelRef.current.contains(e.target as Node)) {
        setNotifPanelOpen(false);
      }
    };
    if (notifPanelOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [notifPanelOpen]);

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
    // Only show full-page spinner on the very first load (before any data exists).
    // Subsequent project switches keep the current UI visible while fetching.
    if (initialLoad) {
      setLoading(true);
    }
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
        _setUsage(usageRes.value);
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
    setInitialLoad(false);
  }

  async function loadNotifications() {
    try {
      const res = await apiRequest<{ notifications: NotificationItem[] }>(
        `/v1/notifications?workspace_id=${selectedProjectId}`,
        {},
        token
      );
      setNotifications(res.notifications || []);
      const unread = (res.notifications || []).filter((n) => !n.read).length;
      setNotifCount(unread);
    } catch (error) {
      console.error("Failed to load notifications:", error);
    }
  }

  async function markAsRead(notificationId: number) {
    try {
      await apiRequest(`/v1/notifications/${notificationId}/read`, { method: "PUT" }, token);
      setNotifications((prev) => prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n)));
      setNotifCount((prev) => Math.max(prev - 1, 0));
    } catch (error) {
      console.error("Failed to mark as read:", error);
    }
  }

  async function markAllAsRead() {
    try {
      await apiRequest("/v1/notifications/read-all", { method: "PUT" }, token);
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setNotifCount(0);
    } catch (error) {
      console.error("Failed to mark all as read:", error);
    }
  }

  function handleNotificationClick(notif: NotificationItem) {
    if (!notif.read) {
      void markAsRead(notif.id);
    }
    if (notif.link) {
      router.push(notif.link);
      setNotifPanelOpen(false);
    }
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
    // Note: loadShell will be triggered automatically via the useEffect that
    // watches selectedProjectId (which updates when setStoredProjectId fires
    // the custom event). No need for router.refresh() or closing the sidebar.
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
        {/* Mobile hamburger */}
        <button
          className="mobile-menu-toggle hidden-desktop"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            position: "fixed",
            top: 14,
            left: 14,
            zIndex: 200,
            background: "var(--brand)",
            border: "none",
            cursor: "pointer",
            fontSize: 18,
            color: "white",
            width: 36,
            height: 36,
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          aria-label="Toggle navigation"
        >
          {sidebarOpen ? "\u2715" : "\u2630"}
        </button>

        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
          {/* Brand */}
          <div className="sidebar-header">
            <Link href="/app/dashboard" className="sidebar-brand" style={{ textDecoration: "none" }}>
              <div className="sidebar-badge">Community OS</div>
              <span className="sidebar-brand-title">RedditFlow</span>
            </Link>
          </div>

          {/* Project Selector — compact */}
          <div className="sidebar-context-card">
            <div className="sidebar-context-head">
              <div>
                <div className="sidebar-context-label">Project</div>
                <div className="sidebar-context-value">{selectedProject?.name || "No project"}</div>
              </div>
            </div>
            <select
              value={String(selectedProject?.id ?? "")}
              onChange={(event) => handleProjectChange(event.target.value)}
              style={{
                width: "100%",
                padding: "6px 10px",
                borderRadius: 8,
                border: "1px solid rgba(255,255,255,0.14)",
                backgroundColor: "rgba(255,255,255,0.08)",
                color: "white",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              {(dash?.projects || []).map((project) => (
                <option key={project.id} value={String(project.id)} style={{ color: "#1a1a2e" }}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          {/* Navigation */}
          <nav className="sidebar-nav">
            {NAV_SECTIONS.map((section) => (
              <div key={section.title} className="nav-section">
                <div className="nav-section-title">{section.title}</div>
                {section.items.map((item: any) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`nav-link ${pathname === item.href ? "active" : ""}`}
                    onClick={() => setSidebarOpen(false)}
                    style={{ textDecoration: "none" }}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                    {item.badge && (
                      <span style={{
                        marginLeft: "auto",
                        fontSize: 10,
                        fontWeight: 700,
                        padding: "2px 7px",
                        borderRadius: 99,
                        background: "rgba(233,69,96,0.15)",
                        color: "#f7b2bc",
                        letterSpacing: "0.02em",
                      }}>
                        {item.badge}
                      </span>
                    )}
                  </Link>
                ))}
              </div>
            ))}
          </nav>

          {/* Sign out */}
          <div className="sidebar-user">
            <button
              className="ghost-button"
              onClick={handleLogout}
              style={{
                width: "100%",
                textAlign: "left",
                color: "rgba(255, 255, 255, 0.6)",
                fontSize: 12,
                padding: "8px 12px",
              }}
            >
              Sign out
            </button>
          </div>
        </aside>

        {/* Main content */}
        <main className="app-main">
          <div className="topbar topbar-elevated">
            <div>
              <h1 className="topbar-title">{currentTitle}</h1>
            </div>
            <div className="topbar-actions">
              {selectedProject && (
                <div className="topbar-project-pill">
                  <span className="topbar-project-label">Project</span>
                  <strong>{selectedProject.name}</strong>
                </div>
              )}
              <div style={{ position: "relative" }} ref={notifPanelRef}>
                <button
                  className="ghost-button"
                  onClick={() => setNotifPanelOpen(!notifPanelOpen)}
                  style={{
                    position: "relative",
                    fontSize: 16,
                    padding: "6px 10px",
                    height: 34,
                    display: "flex",
                    alignItems: "center",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                  }}
                  title="Notifications"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                  {notifCount > 0 && (
                    <span
                      style={{
                        position: "absolute",
                        top: -2,
                        right: -2,
                        backgroundColor: "#e94560",
                        color: "white",
                        borderRadius: "50%",
                        width: 17,
                        height: 17,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 10,
                        fontWeight: 700,
                      }}
                    >
                      {notifCount > 9 ? "9+" : notifCount}
                    </span>
                  )}
                </button>

                {notifPanelOpen && (
                  <div
                    style={{
                      position: "absolute",
                      top: 44,
                      right: 0,
                      width: 340,
                      maxHeight: 440,
                      backgroundColor: "var(--card, white)",
                      border: "1px solid var(--border)",
                      borderRadius: 12,
                      boxShadow: "0 12px 32px rgba(0, 0, 0, 0.15)",
                      zIndex: 1000,
                      display: "flex",
                      flexDirection: "column",
                      fontSize: 13,
                    }}
                  >
                    <div
                      style={{
                        padding: "12px 16px",
                        borderBottom: "1px solid var(--border)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <strong style={{ fontSize: 14 }}>Notifications</strong>
                      {notifications.some((n) => !n.read) && (
                        <button
                          className="ghost-button"
                          onClick={() => void markAllAsRead()}
                          style={{ fontSize: 11, padding: "3px 8px", color: "var(--accent)" }}
                        >
                          Mark all read
                        </button>
                      )}
                    </div>
                    <div style={{ flex: 1, overflowY: "auto", maxHeight: 380 }}>
                      {notifications.length === 0 ? (
                        <div style={{ padding: 24, textAlign: "center", color: "var(--muted)", fontSize: 12 }}>
                          No notifications yet
                        </div>
                      ) : (
                        notifications.map((notif) => (
                          <div
                            key={notif.id}
                            onClick={() => handleNotificationClick(notif)}
                            style={{
                              padding: "10px 16px",
                              borderBottom: "1px solid var(--border)",
                              cursor: notif.link ? "pointer" : "default",
                              backgroundColor: notif.read ? "transparent" : "rgba(99,102,241,0.04)",
                              borderLeft: notif.read ? "none" : "3px solid var(--accent)",
                              transition: "background-color 0.15s",
                            }}
                          >
                            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{notif.title}</div>
                            <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.4 }}>{notif.message}</div>
                            <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4, opacity: 0.7 }}>
                              {new Date(notif.created_at).toLocaleString()}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="app-content">{children}</div>
        </main>
      </div>
    </ToastProvider>
  );
}
