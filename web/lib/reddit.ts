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
 */
export function copyToClipboard(text: string): void {
  navigator.clipboard.writeText(text);
}
