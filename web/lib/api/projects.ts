import { apiRequest } from "../api";

import type { Project, Dashboard } from "../api";

export type { Project, Dashboard };

export async function getProjects(token: string) {
  return apiRequest<Project[]>(
    `/v1/projects`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getProject(token: string, projectId: number) {
  return apiRequest<Project>(
    `/v1/projects/${projectId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createProject(token: string, data: { name: string; description?: string }) {
  return apiRequest<Project>(
    `/v1/projects`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function updateProject(
  token: string,
  projectId: number,
  data: { name?: string; description?: string | null; status?: string },
) {
  return apiRequest<Project>(
    `/v1/projects/${projectId}`,
    { method: "PUT", body: JSON.stringify(data) },
    token,
  );
}

export async function deleteProject(token: string, projectId: number) {
  return apiRequest<{ ok: boolean }>(
    `/v1/projects/${projectId}`,
    { method: "DELETE" },
    token,
  );
}

export async function getDashboard(token: string) {
  return apiRequest<Dashboard>(
    `/v1/dashboard`, { headers: { Authorization: `Bearer ${token}` } }
  );
}
