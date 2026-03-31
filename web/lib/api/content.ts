import { apiRequest } from "../api";

import type { ReplyDraft, PostDraft, PromptTemplate } from "../api";

export type { ReplyDraft, PostDraft, PromptTemplate };

export async function generateReply(token: string, projectId: number, opportunityId: number, promptTemplateId?: number | null) {
  const body = promptTemplateId ? { prompt_template_id: promptTemplateId } : {};
  return apiRequest<ReplyDraft>(
    `/v1/projects/${projectId}/opportunities/${opportunityId}/reply`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) }
  );
}

export async function getReplyDrafts(token: string, projectId: number, opportunityId: number) {
  return apiRequest<ReplyDraft[]>(
    `/v1/projects/${projectId}/opportunities/${opportunityId}/drafts`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createPostDraft(token: string, projectId: number, data: { title: string; body: string; subreddit?: string }) {
  return apiRequest<PostDraft>(
    `/v1/projects/${projectId}/posts`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function getPostDrafts(token: string, projectId: number) {
  return apiRequest<PostDraft[]>(
    `/v1/projects/${projectId}/posts`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function getPrompts(token: string, projectId?: number | null) {
  const suffix = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<PromptTemplate[]>(
    `/v1/prompts${suffix}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function createPrompt(token: string, data: { prompt_type: string; name: string; system_prompt: string; instructions: string; project_id?: number }) {
  return apiRequest<PromptTemplate>(
    `/v1/prompts`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function updatePrompt(token: string, promptId: number, data: Partial<{ prompt_type: string; name: string; system_prompt: string; instructions: string }>) {
  return apiRequest<PromptTemplate>(
    `/v1/prompts/${promptId}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) }
  );
}

export async function deletePrompt(token: string, promptId: number) {
  return apiRequest<void>(
    `/v1/prompts/${promptId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
  );
}
