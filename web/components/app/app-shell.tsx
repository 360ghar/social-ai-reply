"use client";

import { type ReactNode, useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { type Project, apiRequest, isAuthError } from "@/lib/api";
import { getErrorMessage } from "@/types/errors";
import { setStoredProjectId, withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";

import { useAuth } from "@/components/auth/auth-provider";
import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Card } from "@/components/ui/card";
import { Loader2, Bell, ChevronDown, LogOut } from "lucide-react";
import { MobileNav } from "@/components/shared/mobile-nav";

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
      { href: "/app/auto-pipeline", label: "Auto Pipeline", icon: "A", badge: true },
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
  "/app/dashboard": "Dashboard",
  "/app/auto-pipeline": "Overview / Auto Pipeline",
  "/app/visibility": "Monitor / AI Visibility",
  "/app/sources": "Monitor / Source Intel",
  "/app/discovery": "Engage / Opportunity Radar",
  "/app/content": "Engage / Content Studio",
  "/app/subreddits": "Engage / Communities",
  "/app/brand": "Configure / Brand Profile",
  "/app/persona": "Configure / Personas",
  "/app/prompts": "Configure / Prompts",
  "/app/settings": "Settings",
  "/app/analytics": "Overview / Analytics",
};

/** Group notifications into Today / Yesterday / Older buckets. */
function groupNotifications(notifications: NotificationItem[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);

  const groups: { label: string; items: NotificationItem[] }[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Older", items: [] },
  ];

  for (const notif of notifications) {
    const created = new Date(notif.created_at);
    if (created >= today) {
      groups[0].items.push(notif);
    } else if (created >= yesterday) {
      groups[1].items.push(notif);
    } else {
      groups[2].items.push(notif);
    }
  }

  return groups.filter((g) => g.items.length > 0);
}

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

  // Separate state for desktop and mobile notification popovers to avoid conflicts
  const [desktopNotifOpen, setDesktopNotifOpen] = useState(false);
  const [mobileNotifOpen, setMobileNotifOpen] = useState(false);
  const { sidebarOpen, setSidebarOpen } = useUIStore();

  const notificationGroups = useMemo(() => groupNotifications(notifications), [notifications]);

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

    let intervalId: ReturnType<typeof setInterval> | null = null;

    function startPolling() {
      if (intervalId) return;
      void loadNotifications();
      intervalId = setInterval(() => {
        void loadNotifications();
      }, 30000);
    }

    function stopPolling() {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }

    function handleVisibility() {
      if (document.visibilityState === "visible") {
        startPolling();
      } else {
        stopPolling();
      }
    }

    startPolling();
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
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
    } catch (e: unknown) {
      const msg = getErrorMessage(e);
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
      setDesktopNotifOpen(false);
      setMobileNotifOpen(false);
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
      {/* Sidebar (desktop only) */}
      <aside className="hidden md:flex fixed inset-y-0 left-0 z-40 w-56 bg-sidebar text-sidebar-foreground flex-col">
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
            <div className="text-[11px] text-sidebar-foreground/60">{dash?.workspace_name || "Workspace"}</div>
            <div className="flex items-center gap-1 text-sm font-medium text-sidebar-foreground mt-0.5">
              <span className="flex-1 truncate">{selectedProject?.name || "No project"}</span>
              <ChevronDown className="h-3.5 w-3.5 text-sidebar-foreground/50 shrink-0" />
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
            <div key={section.title} className="mb-5">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50 px-3 mb-2">
                {section.title}
              </div>
              {section.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground no-underline transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                      isActive && "border-l-[3px] border-l-primary text-primary font-semibold"
                    )}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <span
                      className={cn(
                        "flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold bg-sidebar-accent/50",
                        isActive && "bg-primary/15 text-primary"
                      )}
                    >
                      {item.icon}
                    </span>
                    <span className="flex-1">{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />
                    )}
                  </Link>
                );
              })}
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
        {/* Topbar */}
        <div className="sticky top-0 z-10 flex items-center justify-between h-14 px-4 md:px-6 border-b border-border bg-card/80 backdrop-blur-sm">
          <div>
            <h1 className="text-lg font-semibold text-foreground">{currentTitle}</h1>
          </div>
          <div className="flex items-center gap-3">
            {/* Notification popover (hidden on mobile) */}
            <div className="hidden md:block">
              <Popover open={desktopNotifOpen} onOpenChange={setDesktopNotifOpen}>
                <span className="relative inline-flex">
                  <PopoverTrigger
                    className="relative flex items-center justify-center h-[34px] px-2.5 rounded-lg border border-border bg-transparent hover:bg-muted cursor-pointer text-foreground"
                  >
                    <Bell className="h-4 w-4" />
                    <span
                      aria-hidden="true"
                      className={cn(
                        "absolute -top-1 -right-1 h-4 w-4 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center text-[10px] font-bold",
                        notifCount === 0 && "hidden"
                      )}
                    >
                      {notifCount > 0 ? (notifCount > 9 ? "9+" : notifCount) : ""}
                    </span>
                  </PopoverTrigger>
                  <span
                    aria-live="polite"
                    aria-atomic="true"
                    className="sr-only"
                  >
                    {notifCount > 0 ? `${notifCount} new notifications` : ""}
                  </span>
                </span>
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
                    {notificationGroups.length === 0 ? (
                      <div className="px-6 py-6 text-center text-muted-foreground text-xs">
                        No notifications yet
                      </div>
                    ) : (
                      notificationGroups.map((group) => (
                        <div key={group.label}>
                          <div className="px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60 bg-muted/30">
                            {group.label}
                          </div>
                          {group.items.map((notif) => (
                            <div
                              key={notif.id}
                              role="button"
                              tabIndex={0}
                              onClick={() => handleNotificationClick(notif)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  handleNotificationClick(notif);
                                }
                              }}
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
                          ))}
                        </div>
                      ))
                    )}
                  </div>
                </PopoverContent>
              </Popover>
            </div>

            {/* Mobile notification bell (simplified) */}
            <div className="md:hidden">
              <Popover open={mobileNotifOpen} onOpenChange={setMobileNotifOpen}>
                <span className="relative inline-flex">
                  <PopoverTrigger
                    className="relative flex items-center justify-center h-8 w-8 rounded-lg bg-transparent border-none cursor-pointer text-foreground"
                  >
                    <Bell className="h-4 w-4" />
                    <span
                      aria-hidden="true"
                      className={cn(
                        "absolute -top-0.5 -right-0.5 h-3 w-3 rounded-full bg-destructive",
                        notifCount === 0 && "hidden"
                      )}
                    />
                  </PopoverTrigger>
                  <span
                    aria-live="polite"
                    aria-atomic="true"
                    className="sr-only"
                  >
                    {notifCount > 0 ? `${notifCount} new notifications` : ""}
                  </span>
                </span>
                <PopoverContent align="end" className="w-72 p-0">
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
                  <div className="max-h-[320px] overflow-y-auto">
                    {notificationGroups.length === 0 ? (
                      <div className="px-6 py-6 text-center text-muted-foreground text-xs">
                        No notifications yet
                      </div>
                    ) : (
                      notificationGroups.map((group) => (
                        <div key={group.label}>
                          <div className="px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60 bg-muted/30">
                            {group.label}
                          </div>
                          {group.items.map((notif) => (
                            <div
                              key={notif.id}
                              role="button"
                              tabIndex={0}
                              onClick={() => handleNotificationClick(notif)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault();
                                  handleNotificationClick(notif);
                                }
                              }}
                              className={`px-4 py-2.5 border-b border-border last:border-b-0 transition-colors ${
                                notif.link ? "cursor-pointer hover:bg-muted/50" : "cursor-default"
                              } ${!notif.read ? "bg-primary/[0.04] border-l-[3px] border-l-primary" : ""}`}
                            >
                              <div className="font-semibold text-[13px] mb-0.5">{notif.title}</div>
                              <div className="text-xs text-muted-foreground leading-snug">{notif.message}</div>
                              <p className="text-xs text-muted-foreground">{new Date(notif.created_at).toLocaleString()}</p>
                            </div>
                          ))}
                        </div>
                      ))
                    )}
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto pb-14 md:pb-0">{children}</div>

        {/* Mobile bottom tab bar */}
        <MobileNav />
      </main>
    </div>
  );
}
