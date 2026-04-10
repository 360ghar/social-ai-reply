import { Skeleton } from "@/components/ui/skeleton";

export default function SourcesLoading() {
  return (
    <div className="flex flex-col gap-8">
      {/* Header row */}
      <div>
        <Skeleton className="h-8 w-44 mb-2" />
        <Skeleton className="h-4 w-80" />
      </div>

      {/* 4-col KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-xl" />
        ))}
      </div>

      {/* Tabs bar */}
      <Skeleton className="h-10 w-80 rounded-lg" />

      {/* Table area */}
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}
