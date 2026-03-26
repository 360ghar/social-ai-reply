import { apiRequest, type Dashboard, type Project } from "./api";
import { resolveProjectId, withProjectId } from "./project";

export async function fetchDashboard(token: string, projectId?: number | null) {
  return apiRequest<Dashboard>(withProjectId("/v1/dashboard", projectId), {}, token);
}

export function getCurrentProject(dashboard: Dashboard): Project | null {
  const projectId = resolveProjectId(dashboard.projects);
  if (!projectId) {
    return null;
  }
  return dashboard.projects.find((project) => project.id === projectId) ?? null;
}
