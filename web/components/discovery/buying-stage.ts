/**
 * Buying-stage helpers shared by the inbox row badges and the stage filter
 * tabs. Stages are ordered by funnel depth (top → bottom).
 */

export const BUYING_STAGES = [
  "unaware",
  "problem_aware",
  "solution_seeking",
  "comparing",
  "evaluating",
  "ready_to_buy",
  "post_purchase",
] as const;

/** Stages worth shouting about — highlighted with accent styling. */
export const HIGH_INTENT_STAGES: ReadonlySet<string> = new Set(["evaluating", "ready_to_buy"]);

/** ready_to_buy → "Ready to buy" */
export function humanizeStage(stage: string): string {
  const label = stage.replace(/_/g, " ").trim();
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** Funnel position used to order stage chips; unknown stages sort last. */
export function stageIndex(stage: string): number {
  const index = (BUYING_STAGES as readonly string[]).indexOf(stage);
  return index === -1 ? BUYING_STAGES.length : index;
}

/**
 * Badge classes color-coded by funnel depth: muted at the top of the funnel,
 * warming up through info/primary, and success for bottom-of-funnel buyers.
 */
export function stageBadgeClass(stage: string): string {
  switch (stage) {
    case "ready_to_buy":
      return "bg-success/10 text-success border-success/30";
    case "evaluating":
      return "bg-warning/10 text-warning border-warning/30";
    case "comparing":
      return "bg-primary/10 text-primary border-primary/20";
    case "solution_seeking":
      return "bg-info/10 text-info border-info/20";
    case "problem_aware":
      return "bg-info/5 text-info/80 border-info/10";
    default:
      // unaware, post_purchase, unknown
      return "bg-muted text-muted-foreground border-border";
  }
}
