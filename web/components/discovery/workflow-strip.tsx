"use client";

import type { RefObject } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface WorkflowStep {
  label: string;
  count: number;
  done: boolean;
  ref: RefObject<HTMLDivElement | null>;
}

interface WorkflowStripProps {
  steps: WorkflowStep[];
}

/** Horizontal step indicator (Signals → Communities → Queue) with scroll-to-section. */
export function WorkflowStrip({ steps }: WorkflowStripProps) {
  const currentStep = steps.findIndex((step) => !step.done);

  return (
    <Card>
      <CardContent className="py-3">
        <div className="flex items-center justify-center gap-1">
          {steps.map((step, i) => (
            <div key={step.label} className="flex items-center">
              <button
                type="button"
                onClick={() => step.ref.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors hover:bg-muted"
              >
                <span
                  className={cn(
                    "flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium transition-colors",
                    step.done
                      ? "bg-primary text-primary-foreground"
                      : i === currentStep
                        ? "bg-primary/10 text-primary ring-2 ring-primary/30"
                        : "bg-muted text-muted-foreground"
                  )}
                >
                  {step.done ? "✓" : i + 1}
                </span>
                <span className="text-sm font-medium text-foreground">{step.label}</span>
                <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
                  {step.count}
                </Badge>
              </button>
              {i < steps.length - 1 && (
                <div className={cn("h-0.5 w-6", step.done ? "bg-primary" : "bg-muted")} />
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
