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

export async function getDashboard(token: string) {
  return apiRequest<Dashboard>(
    `/v1/dashboard`, { headers: { Authorization: `Bearer ${token}` } }
  );
}
