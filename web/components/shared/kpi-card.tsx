"use client";

import type { ElementType } from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";

export interface KPICardProps {
  label: string;
  value: string | number;
  trend?: { value: number; direction: "up" | "down" };
  icon?: ElementType;
  className?: string;
}

interface KPIGridProps {
  cards: KPICardProps[];
  columns?: 2 | 3 | 4;
  className?: string;
}

export function KPICard({
  label,
  value,
  trend,
  icon: Icon,
  className,
}: KPICardProps) {
  return (
    <Card className={cn("p-5 shadow-sm hover:shadow-md transition-shadow", className)}>
      <CardContent className="p-0 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {label}
          </span>
          {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold tracking-tight">{value}</span>
          {trend && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 text-xs font-semibold",
                trend.direction === "up"
                  ? "text-success"
                  : "text-destructive"
              )}
            >
              {trend.direction === "up" ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {trend.value}%
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function KPIGrid({
  cards,
  columns = 4,
  className,
}: KPIGridProps) {
  return (
    <div
      className={cn(
        "grid gap-5",
        columns === 2 && "grid-cols-2",
        columns === 3 && "grid-cols-1 sm:grid-cols-3",
        columns === 4 && "grid-cols-2 lg:grid-cols-4",
        className
      )}
    >
      {cards.map((card) => (
        <KPICard key={card.label} {...card} />
      ))}
    </div>
  );
}
