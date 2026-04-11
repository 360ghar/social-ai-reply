import { Skeleton } from "@/components/ui/skeleton";

export default function AutoPipelineLoading() {
  return (
    <div className="grid gap-8 max-w-[1000px] mx-auto">
      {/* Header row */}
      <div>
        <Skeleton className="h-8 w-36 mb-2" />
        <Skeleton className="h-4 w-80" />
      </div>

      {/* Centered input card */}
      <div className="py-12 px-8 rounded-xl">
        <div className="flex flex-col items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-12 w-full max-w-lg rounded-xl" />
          <Skeleton className="h-12 w-full max-w-lg rounded-xl" />
        </div>
      </div>
    </div>
  );
}
