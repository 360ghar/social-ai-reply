"use client";

import { useEffect } from "react";
import { useProjectStore } from "@/stores/project-store";

export function useSelectedProjectId() {
  const syncFromStorage = useProjectStore((s) => s.syncFromStorage);

  useEffect(() => {
    syncFromStorage();
  }, [syncFromStorage]);

  return useProjectStore((s) => s.selectedProjectId);
}
