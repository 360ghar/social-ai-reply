"use client";

import { type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { type Project, apiRequest, isAuthError } from "@/lib/api";
import { setStoredProjectId, withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";

import { useAuth } from "@/components/auth/auth-provider";
import { useUIStore } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Card } from "@/components/ui/card";
import { Loader2, Bell, Menu, X, LogOut } from "lucide-react";

interface DashData {
  workspace_name?: string;
  projects?: Project[];
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
  const selectedProjectId = useSelectedProjectId();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  const { sidebarOpen, toggleSidebar, setSidebarOpen, notifPanelOpen, setNotifPanelOpen } = useUIStore();

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedProjectId]);

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
      const [dashRes, notifRes] = await Promise.allSettled([
        apiRequest<DashData>(withProjectId("/v1/dashboard", projectId), {}, token),
        apiRequest<NotificationData>("/v1/notifications", {}, token),
      ]);

      if (dashRes.status === "fulfilled") {
        setDash(dashRes.value);
      }
      if (notifRes.status === "fulfilled") {
        setNotifCount(notifRes.value.unread_count || 0);
      }

      const dashFailed = dashRes.status === "rejected" && isAuthError(dashRes.reason);
      if (dashFailed) {
        void logout();
        router.replace("/login");
        return;
      }
    } catch (e: any) {
      const msg = e?.message || "";
      if (isAuthError(e)) {
        void logout();
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
    void logout();
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
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="mt-4 text-muted-foreground">Loading your workspace...</p>
        </div>
      </div>
    );
  }

  if (error && !dash) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Card className="max-w-sm text-center p-6">
          <h3 className="text-sm font-semibold">Something went wrong</h3>
          <p className="mt-1 text-sm text-muted-foreground">{error}</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => {
              setError("");
              void loadShell(selectedProjectId);
            }}
          >
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      {/* Mobile hamburger */}
      <button
        className="fixed top-3.5 left-3.5 z-50 md:hidden flex items-center justify-center h-9 w-9 rounded-lg bg-primary text-primary-foreground border-none cursor-pointer"
        onClick={toggleSidebar}
        aria-label="Toggle navigation"
      >
        {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-56 bg-sidebar text-sidebar-foreground flex flex-col transition-transform duration-200 md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand */}
        <div className="p-6">
          <Link href="/app/dashboard" className="flex items-center gap-2 text-sidebar-foreground no-underline">
            <div className="rounded-md bg-sidebar-primary/10 px-2 py-0.5 text-[10px] font-bold text-sidebar-primary">
              Community OS
            </div>
            <span className="text-lg font-bold">RedditFlow</span>
          </Link>
        </div>

        {/* Project Selector */}
        <div className="rounded-lg bg-sidebar-accent p-3 mx-3 mt-0">
          <div>
            <div className="text-[11px] text-sidebar-foreground/60">Project</div>
            <div className="text-sm font-medium text-sidebar-foreground">
              {selectedProject?.name || "No project"}
            </div>
          </div>
          <select
            value={String(selectedProject?.id ?? "")}
            onChange={(event) => handleProjectChange(event.target.value)}
            className="w-full rounded-lg border border-sidebar-border bg-sidebar-accent/50 text-sidebar-foreground px-2.5 py-1.5 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-sidebar-ring mt-2"
          >
            {(dash?.projects || []).map((project) => (
              <option key={project.id} value={String(project.id)} className="text-foreground">
                {project.name}
              </option>
            ))}
          </select>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-4">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50 px-3 mb-2">
                {section.title}
              </div>
              {section.items.map((item: any) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-sidebar-foreground no-underline transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground ${
                    pathname === item.href ? "bg-sidebar-accent text-sidebar-accent-foreground" : ""
                  }`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold bg-sidebar-accent/50">
                    {item.icon}
                  </span>
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <span className="ml-auto text-[10px] font-bold px-1.5 py-px rounded-full bg-destructive/15 text-destructive">
                      {item.badge}
                    </span>
                  )}
                </Link>
              ))}
            </div>
          ))}
        </nav>

        {/* Sign out */}
        <div className="p-4 border-t border-sidebar-border">
          <Button
            variant="ghost"
            className="w-full justify-start text-sidebar-foreground/60 text-xs h-auto py-2 px-3"
            onClick={handleLogout}
          >
            <LogOut className="h-3 w-3 mr-2" />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 md:ml-56">
        <div className="sticky top-0 z-10 flex items-center justify-between h-14 px-6 border-b border-border bg-card/80 backdrop-blur-sm">
          <div>
            <h1 className="text-lg font-semibold text-foreground">{currentTitle}</h1>
          </div>
          <div className="flex items-center gap-3">
            {selectedProject && (
              <div className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs">
                <span className="text-muted-foreground">Project</span>
                <strong>{selectedProject.name}</strong>
              </div>
            )}

            <Popover open={notifPanelOpen} onOpenChange={setNotifPanelOpen}>
              <PopoverTrigger
                className="relative flex items-center justify-center h-[34px] px-2.5 rounded-lg border border-border bg-transparent hover:bg-muted cursor-pointer text-foreground"
              >
                <Bell className="h-4 w-4" />
                {notifCount > 0 && (
                  <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center text-[10px] font-bold">
                    {notifCount > 9 ? "9+" : notifCount}
                  </span>
                )}
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80 p-0">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                  <strong className="text-sm">Notifications</strong>
                  {notifications.some((n) => !n.read) && (
                    <Button
                      variant="ghost"
                      size="xs"
                      className="text-xs text-primary"
                      onClick={() => void markAllAsRead()}
                    >
                      Mark all read
                    </Button>
                  )}
                </div>
                <div className="max-h-[380px] overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="px-6 py-6 text-center text-muted-foreground text-xs">
                      No notifications yet
                    </div>
                  ) : (
                    notifications.map((notif) => (
                      <div
                        key={notif.id}
                        onClick={() => handleNotificationClick(notif)}
                        className={`px-4 py-2.5 border-b border-border last:border-b-0 transition-colors ${
                          notif.link ? "cursor-pointer hover:bg-muted/50" : "cursor-default"
                        } ${!notif.read ? "bg-primary/[0.04] border-l-[3px] border-l-primary" : ""}`}
                      >
                        <div className="font-semibold text-[13px] mb-0.5">{notif.title}</div>
                        <div className="text-xs text-muted-foreground leading-snug">{notif.message}</div>
                        <div className="text-[11px] text-muted-foreground mt-1 opacity-70">
                          {new Date(notif.created_at).toLocaleString()}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>
        <div className="flex-1 overflow-auto">{children}</div>
      </main>
    </div>
  );
}
