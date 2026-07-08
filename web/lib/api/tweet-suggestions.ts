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
  error_message: string | null;
  created_at: string;
};

export type GenerateSuggestionsRequest = {
  days: number;
  platforms: SuggestionPlatform[];
};

export type GenerateSuggestionsResponse = {
  generated: number;
  suggestions: TweetSuggestion[];
};

export type ListSuggestionsParams = {
  status?: SuggestionStatus;
  platform?: SuggestionPlatform;
  from?: string;
  to?: string;
};

export async function generateSuggestions(
  token: string,
  data: GenerateSuggestionsRequest,
): Promise<GenerateSuggestionsResponse> {
  const allSuggestions: TweetSuggestion[] = [];
  for (const platform of data.platforms) {
    const body = { days: data.days, platform };
    const res = await apiRequest<GenerateSuggestionsResponse>(
      "/v1/suggestions/generate",
      { method: "POST", body: JSON.stringify(body) },
      token,
    );
    allSuggestions.push(...res.suggestions);
  }
  return { generated: allSuggestions.length, suggestions: allSuggestions };
}

export async function listSuggestions(
  token: string,
  params?: ListSuggestionsParams,
): Promise<TweetSuggestion[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.platform) searchParams.set("platform", params.platform);
  if (params?.from) searchParams.set("from", params.from);
  if (params?.to) searchParams.set("to", params.to);
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
