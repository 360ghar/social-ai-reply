import { apiRequest } from "../api";

import type { Keyword, SubredditAnalysis, MonitoredSubreddit, Opportunity } from "../api";

export type { Keyword, SubredditAnalysis, MonitoredSubreddit, Opportunity };

export async function getKeywords(token: string, projectId: number) {
  return apiRequest<Keyword[]>(
    `/v1/discovery/keywords?project_id=${projectId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createKeyword(token: string, projectId: number, data: { keyword: string; rationale?: string; priority_score?: number }) {
  return apiRequest<Keyword>(
    `/v1/discovery/keywords?project_id=${projectId}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deleteKeyword(token: string, projectId: number, keywordId: number) {
  return apiRequest<void>(
    `/v1/discovery/keywords/${keywordId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getSubreddits(token: string, projectId: number) {
  return apiRequest<MonitoredSubreddit[]>(
    `/v1/discovery/subreddits?project_id=${projectId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function addSubreddit(token: string, projectId: number, data: { name: string }) {
  return apiRequest<MonitoredSubreddit>(
    `/v1/discovery/subreddits?project_id=${projectId}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function removeSubreddit(token: string, projectId: number, subredditId: number) {
  return apiRequest<void>(
    `/v1/discovery/subreddits/${subredditId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function triggerScan(token: string, projectId: number) {
  return apiRequest<{ id: string; status: string }>(
    `/v1/scans?project_id=${projectId}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ project_id: projectId }) }
  );
}

export async function getScanStatus(token: string, scanId: string) {
  return apiRequest<{ id: string; status: string; opportunities_found: number }>(
    `/v1/scans/${scanId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getOpportunities(token: string, projectId: number, status?: string) {
  const params = new URLSearchParams({ project_id: String(projectId) });
  if (status) params.set("status", status);
  return apiRequest<Opportunity[]>(
    `/v1/opportunities?${params.toString()}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}
