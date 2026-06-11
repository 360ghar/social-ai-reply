import { apiRequest } from "../api";

export interface OpportunityFeedback {
  opportunity_id: number;
  action: "saved" | "ignored";
  original_score: number;
}

/**
 * Fire-and-forget feedback signal sent when a user approves/ignores an
 * opportunity from the inbox. Errors (including 404 — the endpoint may not
 * exist yet) are swallowed silently; this must never disrupt the UI flow.
 */
export async function sendOpportunityFeedback(
  token: string | null | undefined,
  feedback: OpportunityFeedback
): Promise<void> {
  try {
    await apiRequest<unknown>("/v1/feedback", { method: "POST", body: JSON.stringify(feedback) }, token);
  } catch {
    // Best-effort only — swallow silently.
  }
}
