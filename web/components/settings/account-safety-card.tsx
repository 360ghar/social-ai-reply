"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getAccountSafety, type AccountSafety } from "@/lib/api/reddit";
import { getErrorMessage } from "@/types/errors";
import { cn } from "@/lib/utils";

interface AccountSafetyCardProps {
  token: string | null | undefined;
  accountId: number;
}

function scoreColorClass(score: number): string {
  if (score >= 70) return "text-success";
  if (score >= 40) return "text-amber-600 dark:text-amber-400";
  return "text-destructive";
}

function barColorClass(used: number, cap: number): string {
  if (cap <= 0 || used >= cap) return "bg-destructive";
  if (used / cap >= 0.75) return "bg-amber-500";
  return "bg-primary";
}

function UsageBar({ label, used, cap }: { label: string; used: number; cap: number }) {
  const pct = cap > 0 ? Math.min((used / cap) * 100, 100) : 100;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">
          {used}/{cap}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all", barColorClass(used, cap))}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Compact posting-safety panel for a connected Reddit account.
 * Lazily fetches the safety assessment when the card mounts (i.e. when
 * the Reddit settings tab is opened).
 */
export function AccountSafetyCard({ token, accountId }: AccountSafetyCardProps) {
  const [safety, setSafety] = useState<AccountSafety | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    getAccountSafety(token, accountId)
      .then((result) => {
        if (cancelled) return;
        setSafety(result);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(getErrorMessage(err));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, accountId]);

  if (loading) {
    return (
      <div className="mt-3 flex items-center gap-2 rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Checking account safety...
      </div>
    );
  }

  if (loadError || !safety) {
    return (
      <div className="mt-3 rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
        Safety check unavailable{loadError ? `: ${loadError}` : "."}
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border bg-muted/30 p-3">
      {safety.shadowban_suspected && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-2.5 text-xs font-medium text-destructive">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Shadowban suspected. Recent posts from this account may be invisible to other users — pause
            posting and verify the account from a logged-out browser.
          </span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">Safety score</span>
        <span className={cn("text-sm font-bold tabular-nums", scoreColorClass(safety.score))}>
          {safety.score}/100
        </span>
        <Badge variant="outline" className="capitalize text-[11px]">
          {safety.tier} tier
        </Badge>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 sm:gap-4">
        <UsageBar label="Posted today" used={safety.posted_today} cap={safety.daily_cap} />
        <UsageBar label="Posted this week" used={safety.posted_this_week} cap={safety.weekly_cap} />
      </div>

      {safety.warnings.length > 0 && (
        <ul className="space-y-1">
          {safety.warnings.map((warning) => (
            <li
              key={warning}
              className="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-400"
            >
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{warning}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
