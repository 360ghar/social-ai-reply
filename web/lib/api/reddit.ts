import { apiRequest } from "../api";

export interface RedditAccount {
  id: number;
  username: string;
  karma?: number;
  is_active: boolean;
  connected_at?: string;
}

export interface PublishedPost {
  id: string;
  type: string;
  subreddit: string;
  title?: string;
  content: string;
  status: string;
  upvotes?: number;
  permalink: string;
  published_at?: string;
}

export async function getRedditAccounts(token: string): Promise<RedditAccount[]> {
  const result = await apiRequest<{ items: RedditAccount[] }>("/v1/reddit/accounts", {}, token);
  return result.items;
}

export async function connectReddit(token: string): Promise<{ auth_url: string; message: string }> {
  return apiRequest<{ auth_url: string; message: string }>(
    "/v1/reddit/connect",
    { method: "POST", body: JSON.stringify({}) },
    token,
  );
}

export async function disconnectRedditAccount(token: string, accountId: number): Promise<void> {
  return apiRequest<void>(`/v1/reddit/accounts/${accountId}`, { method: "DELETE" }, token);
}

export async function postToReddit(
  token: string,
  data: {
    reddit_account_id: number;
    project_id: number;
    type: "comment" | "post";
    subreddit: string;
    content: string;
    title?: string;
    parent_post_id?: string;
    campaign_id?: number;
  },
): Promise<PublishedPost> {
  return apiRequest<PublishedPost>(
    "/v1/reddit/post",
    { method: "POST", body: JSON.stringify(data) },
    token,
  );
}

export async function getPublishedPosts(
  token: string,
  projectId?: number | null,
  limit = 20,
  offset = 0,
): Promise<{ items: PublishedPost[] }> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (projectId) params.set("project_id", String(projectId));
  return apiRequest<{ items: PublishedPost[] }>(`/v1/reddit/published?${params.toString()}`, {}, token);
}

export async function checkPublishedPostStatus(
  token: string,
  postId: string,
): Promise<{ id: string; status: string; upvotes: number; last_checked_at: string | null }> {
  return apiRequest<{ id: string; status: string; upvotes: number; last_checked_at: string | null }>(
    `/v1/reddit/published/${postId}/check`,
    { method: "POST" },
    token,
  );
}
