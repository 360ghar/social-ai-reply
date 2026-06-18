"use client";

import { Button } from "@/components/ui/button";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold">Page Error</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          This page encountered an error. Try again, or navigate elsewhere.
        </p>
        {error.message && (
          <p className="mt-4 rounded-md bg-muted p-3 text-xs text-muted-foreground">
            {error.message}
          </p>
        )}
        <Button className="mt-6" onClick={reset}>
          Retry
        </Button>
      </div>
    </div>
  );
}
