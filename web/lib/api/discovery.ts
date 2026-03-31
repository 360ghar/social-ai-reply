import { apiRequest } from "../api";

import type { Keyword, SubredditAnalysis, MonitoredSubreddit, Opportunity } from "../api";

export type { Keyword, SubredditAnalysis, MonitoredSubreddit, Opportunity };

export async function getKeywords(token: string, projectId: number) {
  return apiRequest<Keyword[]>(
    `/v1/projects/${projectId}/keywords`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createKeyword(token: string, projectId: number, data: { keyword: string; rationale?: string; priority_score?: number }) {
  return apiRequest<Keyword>(
    `/v1/projects/${projectId}/keywords`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deleteKeyword(token: string, projectId: number, keywordId: number) {
  return apiRequest<void>(
    `/v1/projects/${projectId}/keywords/${keywordId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getSubreddits(token: string, projectId: number) {
  return apiRequest<MonitoredSubreddit[]>(
    `/v1/projects/${projectId}/subreddits`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function addSubreddit(token: string, projectId: number, data: { name: string }) {
  return apiRequest<MonitoredSubreddit>(
    `/v1/projects/${projectId}/subreddits`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function removeSubreddit(token: string, projectId: number, subredditId: number) {
  return apiRequest<void>(
    `/v1/projects/${projectId}/subreddits/${subredditId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function triggerScan(token: string, projectId: number) {
  return apiRequest<{ scan_run_id: string }>(
    `/v1/projects/${projectId}/scans`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getScanStatus(token: string, projectId: number, scanRunId: string) {
  return apiRequest<{ status: string; progress?: number }>(
    `/v1/projects/${projectId}/scans/${scanRunId}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getOpportunities(token: string, projectId: number) {
  return apiRequest<Opportunity[]>(
    `/v1/projects/${projectId}/opportunities`, { headers: { Authorization: `Bearer ${token}` } }
  );
}
