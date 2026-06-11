"use client";

/**
 * Generic keyboard-shortcut hook.
 *
 * Takes a map of `event.key` → handler and attaches a single window keydown
 * listener. Events are ignored when:
 * - the target is an input, textarea, select, or contenteditable element
 * - a meta/ctrl/alt modifier is pressed (plain Shift is allowed so shifted
 *   keys like "?" can be bound via their produced `event.key`)
 */

import { useEffect, useRef } from "react";

export type ShortcutHandler = (event: KeyboardEvent) => void;
export type ShortcutMap = Record<string, ShortcutHandler>;

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

export function useKeyboardShortcuts(shortcuts: ShortcutMap, enabled = true) {
  // Keep the latest handlers in a ref so the listener never goes stale and
  // we only attach/detach once per `enabled` change.
  const shortcutsRef = useRef<ShortcutMap>(shortcuts);
  shortcutsRef.current = shortcuts;

  useEffect(() => {
    if (!enabled) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      if (isEditableTarget(event.target)) {
        return;
      }
      const handler = shortcutsRef.current[event.key];
      if (handler) {
        event.preventDefault();
        handler(event);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [enabled]);
}
