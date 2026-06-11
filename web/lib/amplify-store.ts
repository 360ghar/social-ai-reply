import type { AmplifyDraft } from "@/lib/api/amplify";

/**
 * Session-scoped handoff store for amplified drafts.
 *
 * The amplify API exposes create/update/publish but no GET, so the Content
 * page stashes drafts it creates here and the Content Studio editor reads
 * them back (keyed by the `amplifyDraft` query param). Drafts survive
 * client-side navigation and reloads within the tab session.
 */

const STORAGE_KEY = "rf-amplify-drafts";
const MAX_DRAFTS = 20;

export function loadAmplifyDrafts(): AmplifyDraft[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as AmplifyDraft[]) : [];
  } catch {
    return [];
  }
}

export function rememberAmplifyDraft(draft: AmplifyDraft): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const drafts = [draft, ...loadAmplifyDrafts().filter((d) => d.id !== draft.id)].slice(0, MAX_DRAFTS);
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(drafts));
  } catch {
    // Quota/serialization failures are non-fatal: the editor just won't
    // show the draft after navigation.
  }
}
