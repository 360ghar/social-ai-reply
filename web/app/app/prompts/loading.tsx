import { Skeleton } from "@/components/ui/skeleton";

export default function PromptsLoading() {
  return (
    <div className="grid gap-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-8 w-40 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-36 rounded-lg" />
      </div>

      {/* Tabs bar */}
      <Skeleton className="h-10 w-64 rounded-lg" />

      {/* 3-col card grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-44 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
