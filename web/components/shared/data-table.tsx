"use client";

import type { ElementType, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";

export interface ColumnDef<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  emptyState?: {
    icon?: ElementType;
    title: string;
    description?: string;
    action?: { label: string; onClick: () => void };
  };
  className?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  emptyState,
  className,
}: DataTableProps<T>) {
  if (data.length === 0) {
    if (emptyState) {
      return (
        <EmptyState
          icon={emptyState.icon}
          title={emptyState.title}
          description={emptyState.description}
          action={emptyState.action}
        />
      );
    }
    return (
      <EmptyState
        icon={Loader2}
        title="No data"
        description="No items to display"
      />
    );
  }

  return (
    <div className={cn("w-full", className)}>
      {/* Desktop table */}
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col.key} className={col.className}>
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row, rowIndex) => (
              <TableRow key={(row as Record<string, unknown>).id?.toString() ?? rowIndex}>
                {columns.map((col) => (
                  <TableCell key={col.key} className={col.className}>
                    {col.render
                      ? col.render(row)
                      : (row[col.key] as ReactNode) ?? ""}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile cards */}
      <div className="flex flex-col gap-3 md:hidden">
        {data.map((row, rowIndex) => (
          <Card key={(row as Record<string, unknown>).id?.toString() ?? rowIndex}>
            <CardContent className="p-4 flex flex-col gap-2">
              {columns.map((col) => (
                <div key={col.key} className="flex items-start justify-between gap-2">
                  <span className="text-xs font-medium text-muted-foreground uppercase shrink-0">
                    {col.header}
                  </span>
                  <span className="text-sm text-right">
                    {col.render
                      ? col.render(row)
                      : (row[col.key] as ReactNode) ?? ""}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
