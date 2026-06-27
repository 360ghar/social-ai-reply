"use client";

import { useEffect, useState } from "react";
import { Loader2, Zap, CheckCircle2, Circle, AlertCircle, ArrowRight, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api";
import {
  triggerScan,
  getScanStatus,
  getOpportunities,
  type ScanRun,
} from "@/lib/api/discovery";
import { useToast } from "@/stores/toast";
import { useRouter } from "next/navigation";
import type { StepStatus } from "@/stores/workflow-store";
import { cn } from "@/lib/utils";

interface ReadinessItem {
  label: string;
  ok: boolean;
  href: string;
}

interface Props {
  token: string;
  projectId: number | null;
  readiness: ReadinessItem[];
  onStatusChange: (status: StepStatus) => void;
}

const SCAN_PHASES = [
  "Fetching posts from communities",
  "Scoring relevance with AI",
  "Detecting competitor mentions",
  "Generating draft replies",
];

export function StepLaunch({ token, projectId, readiness, onStatusChange }: Props) {
  const { success, error, warning } = useToast();
  const router = useRouter();
  const [scanning, setScanning] = useState(false);
  const [scanRun, setScanRun] = useState<ScanRun | null>(null);
  const [opportunityCount, setOpportunityCount] = useState<number | null>(null);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [platforms, setPlatforms] = useState<string[]>(["reddit"]);

  const readyCount = readiness.filter((r) => r.ok).length;
  const canScan = readyCount >= 2 && !!projectId; // need at minimum company + communities

  // Fake phase animation while scanning
  useEffect(() => {
    if (!scanning) return;
    const iv = setInterval(() => {
      setPhaseIndex((i) => (i + 1) % SCAN_PHASES.length);
    }, 3500);
    return () => clearInterval(iv);
  }, [scanning]);

  // Poll scan status
  useEffect(() => {
    if (!scanRun || scanRun.status !== "running") return;
    const iv = setInterval(async () => {
      try {
        const updated = await getScanStatus(token, scanRun.id);
        setScanRun(updated);
        if (updated.status !== "running") {
          clearInterval(iv);
          setScanning(false);
          if (updated.opportunities_found > 0) {
            success("Scan complete", `${updated.opportunities_found} opportunities found`);
            onStatusChange("done");
          } else {
            warning("Scan complete", "No opportunities matched this time. Try broader keywords or communities.");
          }
          // Load opp count
          if (projectId) {
            const opps = await getOpportunities(token, projectId, "all", 200);
            setOpportunityCount(opps.length);
          }
        }
      } catch { /* ignore */ }
    }, 2000);
    return () => clearInterval(iv);
  }, [scanRun?.id, scanRun?.status]);

  async function runScan() {
    if (!projectId) return;
    setScanning(true);
    setScanRun(null);
    setPhaseIndex(0);
    try {
      const run = await triggerScan(token, projectId, {
        search_window_hours: 72,
        max_posts_per_subreddit: 15,
        platforms: platforms.length > 0 ? platforms : undefined,
      });
      setScanRun(run);
      if (run.status !== "running") {
        // Synchronous response
        setScanning(false);
        if (run.opportunities_found > 0) {
          success("Scan complete", `${run.opportunities_found} found`);
          onStatusChange("done");
        } else {
          warning("No matches", "Broaden your keywords or communities.");
        }
      }
    } catch (err) {
      error("Scan failed", err instanceof Error ? err.message : "Unknown error");
      setScanning(false);
    }
  }

  const isRunning = scanRun?.status === "running" || scanning;
  const isDone = scanRun && scanRun.status !== "running" && !scanning;

  return (
    <div className="space-y-6">
      {/* Readiness checklist */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Pipeline Readiness</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {readiness.map((item) => (
            <div
              key={item.label}
              className={cn(
                "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors",
                item.ok
                  ? "border-primary/20 bg-primary/5 text-foreground"
                  : "border-border bg-muted/30 text-muted-foreground"
              )}
            >
              {item.ok ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-primary shrink-0" />
              ) : (
                <Circle className="h-3.5 w-3.5 shrink-0" />
              )}
              <span className="text-xs">{item.label}</span>
              {!item.ok && (
                <a
                  href={item.href}
                  className="ml-auto text-[10px] text-primary hover:underline shrink-0"
                >
                  Set up
                </a>
              )}
            </div>
          ))}
        </div>
        {readyCount < 2 && (
          <p className="text-xs text-yellow-600 dark:text-yellow-400 flex items-center gap-1.5 mt-1">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            Complete at least Company Setup and Communities before scanning.
          </p>
        )}
      </div>

      {/* Platform picker */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Scan Platforms</p>

        {/* Free sources (always available) */}
        <div className="rounded-lg border bg-muted/20 p-3 space-y-2">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">Free Sources</p>
          <div className="flex flex-wrap gap-2">
            {[
              { id: "reddit",      label: "Reddit",       note: "JSON API, no auth" },
              { id: "hackernews",  label: "Hacker News",  note: "Algolia API, free" },
              { id: "github",      label: "GitHub",       note: "REST API, 60 req/hr" },
            ].map(({ id, label, note }) => (
              <button
                key={id}
                onClick={() =>
                  setPlatforms((prev) =>
                    prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
                  )
                }
                title={note}
                className={cn(
                  "text-xs rounded-full border px-3 py-1 transition-colors",
                  platforms.includes(id)
                    ? "bg-primary/10 border-primary/30 text-primary"
                    : "bg-card border-border text-muted-foreground hover:border-primary/30"
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Paid/proxy sources */}
        <div className="rounded-lg border bg-muted/10 p-3 space-y-2 opacity-70">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
            Paid Sources <span className="normal-case font-normal">(requires RAPIDAPI_KEY or proxy)</span>
          </p>
          <div className="flex flex-wrap gap-2">
            {[
              { id: "twitter",   label: "X / Twitter" },
              { id: "linkedin",  label: "LinkedIn" },
              { id: "instagram", label: "Instagram" },
            ].map(({ id, label }) => (
              <button
                key={id}
                onClick={() =>
                  setPlatforms((prev) =>
                    prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
                  )
                }
                className={cn(
                  "text-xs rounded-full border px-3 py-1 transition-colors",
                  platforms.includes(id)
                    ? "bg-primary/10 border-primary/30 text-primary"
                    : "bg-card border-border text-muted-foreground"
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground">
            Consider ScraperAPI ($29/mo) or ScrapFly ($29/mo) for X and LinkedIn — more reliable than RapidAPI free tier.
          </p>
        </div>
      </div>

      {/* Scan status */}
      {isRunning && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <p className="text-sm font-medium">Scan running…</p>
          </div>
          <p className="text-xs text-muted-foreground animate-pulse">{SCAN_PHASES[phaseIndex]}</p>
          <Progress value={null} className="h-1" />
        </div>
      )}

      {isDone && (
        <div className={cn(
          "rounded-lg border p-4 space-y-2",
          scanRun!.opportunities_found > 0
            ? "border-primary/20 bg-primary/5"
            : "border-yellow-500/20 bg-yellow-500/5"
        )}>
          <div className="flex items-center gap-2">
            {scanRun!.opportunities_found > 0 ? (
              <CheckCircle2 className="h-4 w-4 text-primary" />
            ) : (
              <AlertCircle className="h-4 w-4 text-yellow-500" />
            )}
            <p className="text-sm font-semibold">
              {scanRun!.opportunities_found > 0
                ? `${scanRun!.opportunities_found} opportunities found`
                : "No opportunities matched"}
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            {scanRun!.posts_scanned} posts scanned across{" "}
            {scanRun!.subreddits_scanned ?? "—"} communities
          </p>
          {opportunityCount != null && (
            <p className="text-xs text-muted-foreground">
              {opportunityCount} total opportunities in your pipeline
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <Button
          onClick={runScan}
          disabled={isRunning || !canScan}
          size="lg"
          className="gap-2"
        >
          {isRunning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          {isRunning ? "Scanning…" : "Launch Scan"}
        </Button>

        {isDone && scanRun!.opportunities_found > 0 && (
          <Button
            variant="outline"
            onClick={() => router.push("/app/content")}
            className="gap-2"
          >
            <BarChart3 className="h-4 w-4" />
            Review in Content Studio
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
