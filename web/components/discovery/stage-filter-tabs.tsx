"use client";

import { cn } from "@/lib/utils";

import { HIGH_INTENT_STAGES, humanizeStage, stageIndex } from "./buying-stage";

interface StageFilterTabsProps {
  /** Stage → count, computed from the currently loaded (status/search-filtered) list. */
  counts: Record<string, number>;
  totalCount: number;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

/**
 * Loud buying-stage filter chips: "All" plus one chip per stage present in the
 * loaded data, with counts. High-intent stages (evaluating / ready_to_buy)
 * get accent coloring so they jump out.
 */
export function StageFilterTabs({ counts, totalCount, value, onChange, className }: StageFilterTabsProps) {
  const stages = Object.keys(counts).sort((a, b) => stageIndex(a) - stageIndex(b));

  if (stages.length === 0) {
    return null;
  }

  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      <button
        type="button"
        onClick={() => onChange("")}
        className={cn(
          "inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors",
          value === ""
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border bg-muted text-muted-foreground hover:bg-muted/80"
        )}
      >
        All ({totalCount})
      </button>
      {stages.map((stage) => {
        const active = value === stage;
        const highIntent = HIGH_INTENT_STAGES.has(stage);
        return (
          <button
            key={stage}
            type="button"
            onClick={() => onChange(active ? "" : stage)}
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors",
              active
                ? "border-primary bg-primary text-primary-foreground"
                : highIntent
                  ? stage === "ready_to_buy"
                    ? "border-success/40 bg-success/10 text-success hover:bg-success/20"
                    : "border-warning/40 bg-warning/10 text-warning hover:bg-warning/20"
                  : "border-border bg-muted text-muted-foreground hover:bg-muted/80"
            )}
          >
            {humanizeStage(stage)} ({counts[stage]})
          </button>
        );
      })}
    </div>
  );
}
