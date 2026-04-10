import { Skeleton } from "@/components/ui/skeleton";

export default function BrandLoading() {
  return (
    <div className="space-y-8">
      {/* Header row with completeness indicator */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-36" />
        <div className="flex items-center gap-3">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div>
            <Skeleton className="h-3 w-24 mb-1" />
            <Skeleton className="h-4 w-10" />
          </div>
        </div>
      </div>

      {/* Tabs bar */}
      <Skeleton className="h-10 w-72 rounded-lg" />

      {/* Form cards - Identity */}
      <Skeleton className="h-40 rounded-xl" />

      {/* Form cards - Audience */}
      <Skeleton className="h-48 rounded-xl" />

      {/* Form cards - Strategy */}
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}
