"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import {
  LayoutDashboard,
  Radar,
  FileText,
  Eye,
  Menu,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

const TAB_ITEMS = [
  { href: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/discovery", label: "Discovery", icon: Radar },
  { href: "/app/content", label: "Content", icon: FileText },
  { href: "/app/visibility", label: "Visibility", icon: Eye },
];

const MORE_SECTIONS = [
  {
    title: "OVERVIEW",
    items: [
      { href: "/app/dashboard", label: "Dashboard" },
      { href: "/app/auto-pipeline", label: "Auto Pipeline" },
    ],
  },
  {
    title: "MONITOR",
    items: [
      { href: "/app/visibility", label: "AI Visibility" },
      { href: "/app/sources", label: "Source Intel" },
    ],
  },
  {
    title: "ENGAGE",
    items: [
      { href: "/app/discovery", label: "Opportunity Radar" },
      { href: "/app/content", label: "Content Studio" },
      { href: "/app/subreddits", label: "Communities" },
    ],
  },
  {
    title: "CONFIGURE",
    items: [
      { href: "/app/brand", label: "Brand Profile" },
      { href: "/app/persona", label: "Personas" },
      { href: "/app/prompts", label: "Prompts" },
    ],
  },
  {
    title: "SETTINGS",
    items: [{ href: "/app/settings", label: "Settings" }],
  },
];

export function MobileNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-14 items-center justify-around border-t border-border bg-background pb-[env(safe-area-inset-bottom)] shadow-[0_-1px_3px_rgba(120,113,108,0.06)] dark:shadow-[0_-1px_3px_rgba(0,0,0,0.2)] md:hidden">
        {TAB_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex flex-1 flex-col items-center justify-center gap-0.5 py-1 text-xs transition-colors",
                isActive ? "text-primary" : "text-muted-foreground"
              )}
            >
              {isActive && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 h-0.5 w-6 rounded-full bg-primary" />
              )}
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}

        {/* More button */}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          className={cn(
            "relative flex flex-1 flex-col items-center justify-center gap-0.5 py-1 text-xs transition-colors bg-transparent border-none cursor-pointer",
            "text-muted-foreground"
          )}
        >
          <Menu className="h-5 w-5" />
          <span>More</span>
        </button>
      </nav>

      {/* Full nav Sheet */}
      <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
        <SheetContent side="right" className="w-3/4 sm:max-w-sm overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Navigation</SheetTitle>
          </SheetHeader>
          <div className="px-4 pb-6">
            {MORE_SECTIONS.map((section) => (
              <div key={section.title} className="mb-5">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/50 mb-2">
                  {section.title}
                </div>
                {section.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => {
                      setMoreOpen(false);
                      setSidebarOpen(false);
                    }}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm no-underline transition-colors hover:bg-muted",
                      pathname === item.href
                        ? "border-l-[3px] border-l-primary bg-primary/10 text-primary font-semibold"
                        : "text-muted-foreground"
                    )}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            ))}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
