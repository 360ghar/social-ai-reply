import { apiRequest } from "../api";

export type SuggestionPlatform = "x" | "linkedin" | "instagram";
export type SuggestionStatus = "pending" | "approved" | "rejected" | "published";

export type TweetSuggestion = {
  id: number;
  workspace_id: number;
  content: string;
  suggested_for_date: string;
  status: SuggestionStatus;
  platform: SuggestionPlatform;
  scheduled_at: string | null;
  published_at: string | null;
  created_at: string;
};

export type GenerateSuggestionsRequest = {
  day_count: number;
  platforms?: SuggestionPlatform[];
};

export type GenerateSuggestionsResponse = {
  generated: number;
  suggestions: TweetSuggestion[];
};

export type ListSuggestionsParams = {
  status?: SuggestionStatus;
  platform?: SuggestionPlatform;
  date_from?: string;
  date_to?: string;
};

export async function generateSuggestions(
  token: string,
  data: GenerateSuggestionsRequest,
): Promise<GenerateSuggestionsResponse> {
  return apiRequest<GenerateSuggestionsResponse>(
    "/v1/suggestions/generate",
    { method: "POST", body: JSON.stringify(data) },
    token,
  );
}

export async function listSuggestions(
  token: string,
  params?: ListSuggestionsParams,
): Promise<TweetSuggestion[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.platform) searchParams.set("platform", params.platform);
  if (params?.date_from) searchParams.set("date_from", params.date_from);
  if (params?.date_to) searchParams.set("date_to", params.date_to);
  const qs = searchParams.toString();
  return apiRequest<TweetSuggestion[]>(
    `/v1/suggestions${qs ? `?${qs}` : ""}`,
    {},
    token,
  );
}

export async function approveSuggestion(
  token: string,
  suggestionId: number,
): Promise<TweetSuggestion> {
  return apiRequest<TweetSuggestion>(
    `/v1/suggestions/${suggestionId}/approve`,
    { method: "PATCH" },
    token,
  );
}

export async function rejectSuggestion(
  token: string,
  suggestionId: number,
): Promise<TweetSuggestion> {
  return apiRequest<TweetSuggestion>(
    `/v1/suggestions/${suggestionId}/reject`,
    { method: "PATCH" },
    token,
  );
}
