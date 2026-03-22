export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type AuthPayload = {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    is_active: boolean;
  };
  workspace: {
    id: number;
    name: string;
    slug: string;
    role: string;
  };
};

export type Project = {
  id: number;
  workspace_id: number;
  name: string;
  slug: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Opportunity = {
  id: number;
  project_id: number;
  scan_run_id: string | null;
  reddit_post_id: string;
  subreddit_name: string;
  author: string;
  title: string;
  permalink: string;
  body_excerpt: string | null;
  score: number;
  status: string;
  score_reasons: string[];
  keyword_hits: string[];
  rule_risk: string[];
  created_at: string;
  updated_at: string;
  posted_at: string | null;
};

export type ReplyDraft = {
  id: number;
  project_id: number;
  opportunity_id: number;
  content: string;
  rationale: string | null;
  source_prompt: string | null;
  version: number;
  created_at: string;
};

export type Subscription = {
  plan_code: string;
  status: string;
  current_period_end: string | null;
  features: string[];
  limits: Record<string, number>;
};

export type Dashboard = {
  projects: Project[];
  top_opportunities: Opportunity[];
  subscription: Subscription;
};

export type BrandProfile = {
  id: number;
  project_id: number;
  brand_name: string;
  website_url: string | null;
  summary: string | null;
  voice_notes: string | null;
  product_summary: string | null;
  target_audience: string | null;
  call_to_action: string | null;
  reddit_username: string | null;
  linkedin_url: string | null;
  last_analyzed_at: string | null;
};

export type Persona = {
  id: number;
  project_id: number;
  name: string;
  role: string | null;
  summary: string;
  pain_points: string[];
  goals: string[];
  triggers: string[];
  preferred_subreddits: string[];
  source: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Keyword = {
  id: number;
  project_id: number;
  keyword: string;
  rationale: string | null;
  priority_score: number;
  source: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SubredditAnalysis = {
  id: number;
  top_post_types: string[];
  audience_signals: string[];
  posting_risk: string[];
  recommendation: string;
  analyzed_at: string;
};

export type MonitoredSubreddit = {
  id: number;
  project_id: number;
  name: string;
  title: string | null;
  description: string | null;
  subscribers: number;
  activity_score: number;
  fit_score: number;
  rules_summary: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  analyses: SubredditAnalysis[];
};

export type PromptTemplate = {
  id: number;
  project_id: number | null;
  prompt_type: string;
  name: string;
  system_prompt: string;
  instructions: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type WebhookEndpoint = {
  id: number;
  workspace_id: number;
  target_url: string;
  event_types: string[];
  is_active: boolean;
  last_tested_at: string | null;
  created_at: string;
};

export type SecretRecord = {
  id: number;
  workspace_id: number;
  provider: string;
  label: string;
  created_at: string;
  updated_at: string;
};

export function isAuthError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }
  return [
    "Authentication required.",
    "Invalid token.",
    "User not found.",
    "No workspace membership found."
  ].includes(error.message);
}

export async function apiRequest<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail ?? payload.message ?? detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return response.json() as Promise<T>;
}
