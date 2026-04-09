import { create } from "zustand";
import type { Project } from "@/lib/api";
import { getStoredProjectId, setStoredProjectId, PROJECT_CHANGE_EVENT } from "@/lib/project";

interface ProjectState {
  selectedProjectId: number | null;
  projects: Project[];
  setProjectId: (id: number) => void;
  setProjects: (projects: Project[]) => void;
  syncFromStorage: () => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  selectedProjectId: null,
  projects: [],

  setProjectId(id) {
    set({ selectedProjectId: id });
    setStoredProjectId(id);
  },

  setProjects(projects) {
    set((state) => {
      const currentId = state.selectedProjectId;
      if (currentId && projects.some((p) => p.id === currentId)) {
        return { projects };
      }
      return { projects, selectedProjectId: projects[0]?.id ?? null };
    });
  },

  syncFromStorage() {
    set({ selectedProjectId: getStoredProjectId() });
  },
}));

if (typeof window !== "undefined") {
  const sync = () => useProjectStore.getState().syncFromStorage();
  window.addEventListener(PROJECT_CHANGE_EVENT, sync);
  window.addEventListener("storage", sync);
}
