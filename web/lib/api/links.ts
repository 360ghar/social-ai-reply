import { API_BASE, apiRequest } from "../api";

/** A tracked short link used for reply ROI attribution. */
export type TrackedLink = {
  id: number;
  project_id: number;
  code: string;
  destination_url: string;
  opportunity_id: number | null;
  reply_draft_id: number | null;
  utm_params: Record<string, string>;
  created_at: string;
  short_path: string;
  tracked_url: string;
  click_count: number;
};

export type RoiRollupRow = {
  group_by: "subreddit" | "buying_stage" | string;
  key: string;
  links: number;
  clicks: number;
};

export type RoiRollupResponse = {
  project_id: number;
  rows: RoiRollupRow[];
};

/** The shareable short URL is served by the API host (e.g. https://api.example.com/r/abcd). */
export function shortLinkUrl(link: Pick<TrackedLink, "short_path">): string {
  return `${API_BASE}${link.short_path}`;
}

export async function createTrackedLink(
  token: string,
  data: {
    project_id: number;
    destination_url: string;
    opportunity_id?: number | null;
    reply_draft_id?: number | null;
  },
): Promise<TrackedLink> {
  return apiRequest<TrackedLink>("/v1/links", { method: "POST", body: JSON.stringify(data) }, token);
}

export async function getTrackedLinks(token: string, projectId?: number | null): Promise<TrackedLink[]> {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<TrackedLink[]>(`/v1/links${qs}`, {}, token);
}

export async function getRoiRollup(token: string, projectId?: number | null): Promise<RoiRollupResponse> {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<RoiRollupResponse>(`/v1/analytics/roi${qs}`, {}, token);
}
