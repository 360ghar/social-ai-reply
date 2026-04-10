import { Skeleton } from "@/components/ui/skeleton";

export default function SettingsLoading() {
  return (
    <div className="flex flex-col gap-8">
      {/* Header row */}
      <div>
        <Skeleton className="h-8 w-28 mb-2" />
        <Skeleton className="h-4 w-72" />
      </div>

      {/* Tabs bar */}
      <Skeleton className="h-10 w-96 rounded-lg" />

      {/* Form card */}
      <Skeleton className="h-96 rounded-xl" />
    </div>
  );
}
