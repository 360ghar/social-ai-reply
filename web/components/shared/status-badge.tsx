"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { cva } from "class-variance-authority";

type Variant = "success" | "warning" | "error" | "info" | "neutral" | "primary";

/**
 * StatusBadge — Semantic status indicator with optional score-based color resolution.
 *
 * When `score` is provided without `variant`, color is determined by thresholds:
 * - >= 70: success (green)
 * - >= 40: warning (amber)
 * - < 40: error (red)
 *
 * When `variant` is explicitly provided, it takes precedence over `score`.
 * When both are omitted, defaults to "neutral".
 */
interface StatusBadgeProps {
  variant?: Variant;
  score?: number;
  dot?: boolean;
  children?: ReactNode;
  className?: string;
}

const statusBadgeVariants = cva(
  "inline-flex items-center justify-center rounded-full border px-2 py-0.5 text-xs font-semibold",
  {
    variants: {
      variant: {
        success: "bg-success/10 text-success border-success/20",
        warning: "bg-warning/10 text-warning border-warning/20",
        error: "bg-destructive/10 text-destructive border-destructive/20",
        info: "bg-info/10 text-info border-info/20",
        neutral: "bg-muted text-muted-foreground border-border",
        primary: "bg-primary/10 text-primary border-primary/20",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  }
);

const statusDotVariants = cva(
  "inline-block h-1.5 w-1.5 rounded-full",
  {
    variants: {
      variant: {
        success: "bg-success",
        warning: "bg-warning",
        error: "bg-destructive",
        info: "bg-info",
        neutral: "bg-muted-foreground",
        primary: "bg-primary",
      },
    },
  }
);

const statusDotTextVariants = cva(
  "inline-flex items-center gap-1.5 text-xs font-semibold",
  {
    variants: {
      variant: {
        success: "text-success",
        warning: "text-warning",
        error: "text-destructive",
        info: "text-info",
        neutral: "text-muted-foreground",
        primary: "text-primary",
      },
    },
  }
);

// Explicit variant takes precedence; score is only used when variant is not provided.
function resolveVariant(score?: number, variant?: Variant): Variant {
  if (variant) return variant;
  if (score !== undefined) {
    if (score >= 70) return "success";
    if (score >= 40) return "warning";
    return "error";
  }
  return "neutral";
}

export function StatusBadge({
  variant: variantProp,
  score,
  dot = false,
  children,
  className,
}: StatusBadgeProps) {
  const variant = resolveVariant(score, variantProp);
  const content = children ?? (score !== undefined ? score : null);

  if (dot) {
    return (
      <span
        className={statusDotTextVariants({ variant, className })}
      >
        <span className={statusDotVariants({ variant })} />
        {content}
      </span>
    );
  }

  return (
    <span className={statusBadgeVariants({ variant, className })}>
      {content}
    </span>
  );
}
