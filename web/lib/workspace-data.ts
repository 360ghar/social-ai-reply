import { apiRequest, type Dashboard, type Project } from "./api";
import { resolveProjectId } from "./project";

export async function fetchDashboard(token: string) {
  return apiRequest<Dashboard>("/v1/dashboard", {}, token);
}

export function getCurrentProject(dashboard: Dashboard): Project | null {
  const projectId = resolveProjectId(dashboard.projects);
  if (!projectId) {
    return null;
  }
  return dashboard.projects.find((project) => project.id === projectId) ?? null;
}
