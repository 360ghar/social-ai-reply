/**
 * Platform-neutral helpers for rendering an opportunity's source.
 *
 * Opportunities historically came only from Reddit (`subreddit_name`), but the
 * platform is moving toward multi-source discovery (`platform` / `source_name`).
 */

export interface OpportunitySource {
  subreddit_name?: string | null;
  platform?: string | null;
  source_name?: string | null;
}

/** Human-readable label for where an opportunity came from. */
export function sourceLabel(source: OpportunitySource): string {
  if (source.subreddit_name) {
    return `r/${source.subreddit_name}`;
  }
  return source.source_name || source.platform || "Unknown source";
}

/** Platform key for icon rendering (defaults to reddit for subreddit-based rows). */
export function sourcePlatform(source: OpportunitySource): string {
  if (source.platform) {
    return source.platform;
  }
  return source.subreddit_name ? "reddit" : "default";
}
