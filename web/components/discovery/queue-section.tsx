"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Opportunity } from "@/lib/api";

import { FiltersBar, type FilterConfig } from "./filters-bar";
import { OpportunityList, type StatusTab } from "./opportunity-list";

interface QueueSectionProps {
  /** Opportunities already filtered by the page (status / search / etc.). */
  opportunities: Opportunity[];
  totalCount: number;
  statusTabs?: StatusTab[];
  statusFilter: string;
  onStatusFilterChange: (value: string) => void;
  search: { value: string; onChange: (value: string) => void };
  filters?: FilterConfig[];
  generatingReplyId: number | null;
  onGenerateReply: (opportunity: Opportunity) => void;
  emptyAction?: { label: string; onClick: () => void };
}

/** Conversation Queue card: filters bar + tabbed, paginated opportunity list. */
export function QueueSection({
  opportunities,
  totalCount,
  statusTabs,
  statusFilter,
  onStatusFilterChange,
  search,
  filters,
  generatingReplyId,
  onGenerateReply,
  emptyAction,
}: QueueSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          Conversation Queue
          <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
            {opportunities.length}
          </Badge>
        </CardTitle>
        <CardAction>
          <FiltersBar search={search} filters={filters} />
        </CardAction>
      </CardHeader>
      <CardContent>
        <OpportunityList
          opportunities={opportunities}
          totalCount={totalCount}
          statusTabs={statusTabs}
          statusFilter={statusFilter}
          onStatusFilterChange={onStatusFilterChange}
          generatingReplyId={generatingReplyId}
          onGenerateReply={onGenerateReply}
          emptyAction={emptyAction}
        />
      </CardContent>
    </Card>
  );
}
