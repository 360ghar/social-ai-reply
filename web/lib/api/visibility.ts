import { apiRequest } from "../api";

export interface PromptSetItem {
  id: number;
  name: string;
  category: string;
  prompts: string[];
  target_models: string[];
  is_active: boolean;
  schedule: string;
  created_at: string | null;
}

export interface VisibilitySummary {
  total_runs: number;
  brand_mentioned: number;
  share_of_voice: number;
  total_citations: number;
  models: Record<string, { total_runs: number; brand_mentioned: number; share_of_voice: number }>;
}

export interface PromptRunResult {
  id: number;
  prompt_text: string;
  model_name: string;
  status: string;
  brand_mentioned: boolean;
  competitor_mentions: any[];
  sentiment: string | null;
  citations_count: number;
  completed_at: string | null;
}

export interface CitationItem {
  id: number;
  url: string;
  domain: string;
  title: string | null;
  content_type: string | null;
  first_seen_at: string | null;
}

export async function getPromptSets(token: string, projectId?: number | null) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<{ items: PromptSetItem[] }>(
    `/v1/prompt-sets${suffix}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createPromptSet(
  token: string,
  data: { name: string; category: string; prompts: string[]; target_models: string[]; schedule: string },
  projectId?: number | null
) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<{ id: number; name: string }>(
    `/v1/prompt-sets${suffix}`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify(data) }
  );
}

export async function runPromptSet(token: string, id: number, projectId?: number | null) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<{ prompt_set_id: number; results: any[]; total_runs: number }>(
    `/v1/prompt-sets/${id}/run${suffix}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getVisibilitySummary(token: string, projectId?: number | null) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<VisibilitySummary>(
    `/v1/visibility/summary${suffix}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getVisibilityPrompts(token: string, model?: string, limit = 20, offset = 0, projectId?: number | null) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (model) params.set("model", model);
  if (projectId) params.set("project_id", String(projectId));
  return apiRequest<{ items: PromptRunResult[]; total: number }>(
    `/v1/visibility/prompts?${params}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getCitations(token: string, domain?: string, limit = 20, projectId?: number | null) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (domain) params.set("domain", domain);
  if (projectId) params.set("project_id", String(projectId));
  return apiRequest<{ items: CitationItem[]; total: number }>(
    `/v1/citations?${params}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getSourceDomains(token: string, projectId?: number | null) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<{ items: { domain: string; total_citations: number }[] }>(
    `/v1/sources/domains${suffix}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getSourceGaps(token: string, projectId?: number | null) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<{ items: any[] }>(
    `/v1/sources/gaps${suffix}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}
