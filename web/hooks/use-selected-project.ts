"use client";

import { useProjectStore } from "@/stores/project-store";

export function useSelectedProjectId() {
  return useProjectStore((s) => s.selectedProjectId);
}
