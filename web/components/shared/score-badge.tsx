/**
 * ScoreBadge — canonical score display component.
 *
 * Uses semantic color tokens (success/warning/destructive) for proper
 * dark mode support instead of hardcoded Tailwind colors.
 *
 * Thresholds:
 *   >= 70  → success (high fit)
 *   >= 40  → warning (medium fit)
 *    < 40  → destructive (low fit)
 */
import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number;
  className?: string;
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  const colorClass =
    score >= 70
      ? "bg-success/10 text-success border-success/20"
      : score >= 40
        ? "bg-warning/10 text-warning border-warning/20"
        : "bg-destructive/10 text-destructive border-destructive/20";

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
