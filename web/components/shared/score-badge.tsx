/**
 * ScoreBadge — canonical score display component.
 *
 * Color thresholds (reconciled from discovery, sources, and subreddits):
 *   >= 70  → emerald (high fit)
 *   >= 40  → amber   (medium fit)
 *    < 40  → red/destructive (low fit)
 *
 * Styling: uses the more featureful variant from discovery/page.tsx
 * (inline span with explicit bg/border colors) rather than the Badge-wrapper
 * variant used in sources/subreddits, because it renders consistently in both
 * badge and non-badge contexts without importing shadcn Badge.
 */
import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number;
  className?: string;
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  const colorClass =
    score >= 70
      ? "text-emerald-600 border-emerald-300 bg-emerald-50"
      : score >= 40
        ? "text-amber-600 border-amber-300 bg-amber-50"
        : "text-red-600 border-red-300 bg-red-50";

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full border px-2 py-0.5 text-xs font-semibold",
        colorClass,
        className
      )}
    >
      {score}
    </span>
  );
}
