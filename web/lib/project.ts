import type { Project } from "./api";

const STORAGE_KEY = "redditflow-project-id";
const LEGACY_STORAGE_KEY = "reply-radar-project-id";

export function getStoredProjectId(): number | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(STORAGE_KEY) ?? window.localStorage.getItem(LEGACY_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  const parsed = Number(raw);
  if (Number.isFinite(parsed)) {
    window.localStorage.setItem(STORAGE_KEY, String(parsed));
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
  }
  return Number.isFinite(parsed) ? parsed : null;
}

export function setStoredProjectId(projectId: number): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, String(projectId));
  window.localStorage.removeItem(LEGACY_STORAGE_KEY);
}

export function resolveProjectId(projects: Project[]): number | null {
  const stored = getStoredProjectId();
  if (stored && projects.some((project) => project.id === stored)) {
    return stored;
  }
  return projects[0]?.id ?? null;
}
