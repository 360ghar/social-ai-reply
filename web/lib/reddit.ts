/**
 * Shared Reddit utility helpers.
 * Both functions were previously duplicated in content/page.tsx and discovery/page.tsx.
 */

/**
 * Returns a full Reddit URL from a permalink that may or may not already be absolute.
 */
export function redditUrl(permalink: string): string {
  if (permalink.startsWith("http")) {
    return permalink;
  }
  return `https://www.reddit.com${permalink}`;
}

/**
 * Copies `text` to the clipboard.
 * The caller is responsible for showing user feedback after the call.
 * Errors propagate so callers can show failure toasts.
 */
export async function copyText(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}
