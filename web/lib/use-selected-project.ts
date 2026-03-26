"use client";

import { useEffect, useState } from "react";

import { getStoredProjectId, PROJECT_CHANGE_EVENT } from "./project";

export function useSelectedProjectId() {
  const [projectId, setProjectId] = useState<number | null>(() => getStoredProjectId());

  useEffect(() => {
    const sync = () => setProjectId(getStoredProjectId());
    sync();
    window.addEventListener(PROJECT_CHANGE_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(PROJECT_CHANGE_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return projectId;
}
