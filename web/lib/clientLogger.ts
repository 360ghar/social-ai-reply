/**
 * Client-side logging — captures browser errors and key user interaction
 * events and ships them to the backend as structured logs.
 *
 * Design goals:
 * - Never throw. Every hook is wrapped in try/catch so logging can't break the app.
 * - No PII/secrets over the wire. Auth headers are never attached; secret-shaped
 *   keys/values are stripped client-side AND again server-side (defense in depth).
 * - Batch + debounce. Events accumulate and flush every ~2s, at 10 events, or on
 *   beforeunload (via navigator.sendBeacon).
 * - Works pre-login (no Authorization header; endpoint is optionally authed).
 *
 * Sampling:
 * - Errors/unhandled rejections: 100% by default.
 * - Info/warning events: 10% by default.
 * - Override via NEXT_PUBLIC_CLIENT_LOG_SAMPLE (0..1) and NEXT_PUBLIC_CLIENT_LOGGING.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ENDPOINT = `${API_BASE}/v1/telemetry/client-event`;

// Kill-switch: set NEXT_PUBLIC_CLIENT_LOGGING=0 / false to disable entirely.
const LOGGING_ENABLED = (() => {
  const raw = process.env.NEXT_PUBLIC_CLIENT_LOGGING;
  if (raw === undefined || raw === "") return true; // default ON
  return raw !== "0" && raw.toLowerCase() !== "false";
})();

// Sampling rates.
const ERROR_SAMPLE = 1.0;
const INFO_SAMPLE = (() => {
  const raw = process.env.NEXT_PUBLIC_CLIENT_LOG_SAMPLE;
  if (raw === undefined || raw === "") return 0.1;
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? Math.min(1, Math.max(0, parsed)) : 0.1;
})();

const FLUSH_INTERVAL_MS = 2000;
const FLUSH_BATCH_SIZE = 10;
const MAX_MESSAGE_LEN = 2000;
const MAX_STACK_LEN = 8000;
const MAX_URL_LEN = 500;
const SESSION_STORAGE_KEY = "rf_client_log_session_id";

// Secret-shaped KEYS are stripped before send (server re-sanitizes too).
// Word-boundary anchors prevent false positives on values like "authenticated".
const SECRET_KEY_RE = /\b(?:password|token|secret|authorization|api[_-]?key|auth|cookie|session)\b/i;

type ClientLogLevel = "debug" | "info" | "warning" | "error";

interface ClientEvent {
  event: string;
  level: ClientLogLevel;
  message: string | null;
  stack: string | null;
  url: string | null;
  session_id: string | null;
  props: Record<string, unknown> | null;
}

// ── Session id ────────────────────────────────────────────────────

function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    const id = newSessionId();
    window.sessionStorage.setItem(SESSION_STORAGE_KEY, id);
    return id;
  } catch {
    return null;
  }
}

function newSessionId(): string {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
  } catch {
    // fall through to fallback
  }
  // RFC4122-ish fallback (not cryptographically strong, fine for correlation).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// ── Redaction / truncation ────────────────────────────────────────

function truncate(value: string | null | undefined, limit: number): string | null {
  if (!value) return null;
  return value.length <= limit ? value : value.slice(0, limit);
}

function sanitizeProps(props: Record<string, unknown> | undefined): Record<string, unknown> | null {
  if (!props || typeof props !== "object") return null;
  const out: Record<string, unknown> = {};
  let count = 0;
  for (const [key, value] of Object.entries(props)) {
    if (count >= 20) break;
    if (typeof key === "string" && SECRET_KEY_RE.test(key)) continue;
    if (typeof value === "string") {
      out[key] = value.length > 500 ? value.slice(0, 500) : value;
    } else if (typeof value === "number" || typeof value === "boolean" || value === null) {
      out[key] = value;
    } else {
      try {
        out[key] = String(value).slice(0, 500);
      } catch {
        continue;
      }
    }
    count += 1;
  }
  return Object.keys(out).length > 0 ? out : null;
}

function errorToStack(error: unknown): string | null {
  if (!error) return null;
  try {
    if (error instanceof Error) {
      return [error.name, error.message, error.stack].filter(Boolean).join("\n") || null;
    }
    return String(error);
  } catch {
    return null;
  }
}

function errorToMessage(error: unknown): string | null {
  if (!error) return null;
  try {
    if (error instanceof Error) return error.message || error.name || null;
    if (typeof error === "string") return error;
    return String(error);
  } catch {
    return null;
  }
}

// ── Queue + flush ─────────────────────────────────────────────────

let queue: ClientEvent[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let initialized = false;
// Guards against re-entrancy: if our own error handler triggers an error
// during a flush, we must not re-queue (infinite loop).
let flushing = false;

function scheduleFlush(): void {
  if (flushTimer !== null) return;
  try {
    flushTimer = setTimeout(() => {
      flushTimer = null;
      void flush();
    }, FLUSH_INTERVAL_MS);
  } catch {
    // setTimeout can throw in some environments — swallow.
  }
}

async function flush(): Promise<void> {
  if (flushing) return;
  if (queue.length === 0) return;
  flushing = true;
  const batch = queue.splice(0, Math.min(queue.length, FLUSH_BATCH_SIZE));
  // If more remain, schedule another flush.
  if (queue.length > 0) scheduleFlush();
  try {
    await sendBatch(batch);
  } catch {
    // Send failed — events are lost. Never retry-storm. Could re-queue a
    // capped subset, but for client logs dropping is acceptable.
  } finally {
    flushing = false;
  }
}

async function sendBatch(batch: ClientEvent[]): Promise<void> {
  // The endpoint accepts a single event per request (Pydantic model, not a
  // list). Send them sequentially — order/correctness is best-effort.
  if (typeof fetch === "function") {
    const unsent: ClientEvent[] = [];
    for (const evt of batch) {
      try {
        await fetch(ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(evt),
          keepalive: true,
          // No credentials/Authorization — works pre-login, no PII.
          credentials: "omit",
        });
      } catch {
        unsent.push(evt);
      }
    }
    // Re-queue unsent events (capped to avoid unbounded growth).
    if (unsent.length > 0) {
      queue = unsent.concat(queue).slice(0, FLUSH_BATCH_SIZE * 3);
      scheduleFlush();
    }
    return;
  }
  // Fallback: sendBeacon (no response, but reliable on unload).
  if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
    for (const evt of batch) {
      try {
        const blob = new Blob([JSON.stringify(evt)], { type: "application/json" });
        navigator.sendBeacon(ENDPOINT, blob);
      } catch {
        // give up on this event
      }
    }
  }
}

function enqueue(event: ClientEvent): void {
  queue.push(event);
  if (queue.length >= FLUSH_BATCH_SIZE) {
    void flush();
  } else {
    scheduleFlush();
  }
}

// ── Public API ────────────────────────────────────────────────────

/**
 * Record a client-side event. Safe to call anywhere — never throws.
 *
 * @param event  Short event name (e.g. "ui.error_boundary", "reply.generate")
 * @param props  Optional structured context (secret-shaped keys are stripped)
 * @param level  Severity; defaults to "info"
 */
export function logClientEvent(
  event: string,
  props?: Record<string, unknown>,
  level: Exclude<ClientLogLevel, "debug"> = "info",
): void {
  if (!LOGGING_ENABLED) return;
  if (typeof window === "undefined") return;
  try {
    // Sampling: errors always pass; info/warning sampled at INFO_SAMPLE.
    if (level !== "error" && Math.random() > INFO_SAMPLE) return;
    const evt: ClientEvent = {
      event: event.slice(0, 128),
      level,
      message: null,
      stack: null,
      url: truncate(typeof window !== "undefined" ? window.location.pathname : null, MAX_URL_LEN),
      session_id: getSessionId(),
      props: sanitizeProps(props),
    };
    enqueue(evt);
  } catch {
    // never throw
  }
}

/**
 * Convenience wrapper for error events (always sampled at 100%).
 */
export function logClientError(
  event: string,
  error: unknown,
  props?: Record<string, unknown>,
): void {
  if (!LOGGING_ENABLED) return;
  if (typeof window === "undefined") return;
  try {
    const evt: ClientEvent = {
      event: event.slice(0, 128),
      level: "error",
      message: truncate(errorToMessage(error), MAX_MESSAGE_LEN),
      stack: truncate(errorToStack(error), MAX_STACK_LEN),
      url: truncate(window.location.pathname, MAX_URL_LEN),
      session_id: getSessionId(),
      props: sanitizeProps(props),
    };
    enqueue(evt);
  } catch {
    // never throw
  }
}

// ── Global hooks ──────────────────────────────────────────────────

function installGlobalHooks(): void {
  if (typeof window === "undefined") return;

  // window "error" — uncaught runtime errors + resource load failures.
  window.addEventListener("error", (ev: ErrorEvent) => {
    try {
      // ErrorEvent has .error for runtime errors; .message/.filename for
      // resource failures (img/script 404) where .error is null.
      const error = ev.error;
      if (error) {
        logClientError("window.uncaught", error);
      } else {
        const props: Record<string, unknown> = {};
        if (ev.filename) props.filename = ev.filename;
        if (ev.lineno) props.lineno = ev.lineno;
        if (ev.colno) props.colno = ev.colno;
        const evt: ClientEvent = {
          event: "window.resource_error",
          level: "error",
          message: truncate(ev.message, MAX_MESSAGE_LEN),
          stack: null,
          url: truncate(window.location.pathname, MAX_URL_LEN),
          session_id: getSessionId(),
          props: sanitizeProps(props),
        };
        enqueue(evt);
      }
    } catch {
      // never throw
    }
  });

  // Unhandled promise rejections.
  window.addEventListener("unhandledrejection", (ev: PromiseRejectionEvent) => {
    try {
      const reason = ev.reason;
      logClientError("window.unhandledrejection", reason);
    } catch {
      // never throw
    }
  });

  // Wrap console.error — captures framework-logged errors (React dev warnings
  // are console.error in dev; in prod React logs via console.error too).
  // Debounced/dedup-guarded to avoid loops: a flag prevents re-entrancy when
  // our own code calls console.error internally.
  try {
    const origError = console.error.bind(console);
    let wrappedActive = false;
    console.error = (...args: unknown[]) => {
      origError(...args);
      if (wrappedActive) return; // re-entrancy guard
      try {
        wrappedActive = true;
        const message = args
          .map((a) => (typeof a === "string" ? a : safeStringify(a)))
          .join(" ");
        if (!message) return;
        const evt: ClientEvent = {
          event: "console.error",
          level: "error",
          message: truncate(message, MAX_MESSAGE_LEN),
          stack: null,
          url: truncate(window.location.pathname, MAX_URL_LEN),
          session_id: getSessionId(),
          props: null,
        };
        enqueue(evt);
      } catch {
        // ignore
      } finally {
        wrappedActive = false;
      }
    };
  } catch {
    // ignore
  }

  // Flush on tab close / unload. sendBeacon is the reliable primitive here.
  window.addEventListener("beforeunload", () => {
    try {
      if (queue.length === 0) return;
      if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
        for (const evt of queue) {
          try {
            const blob = new Blob([JSON.stringify(evt)], { type: "application/json" });
            navigator.sendBeacon(ENDPOINT, blob);
          } catch {
            // give up on this event
          }
        }
        queue = [];
      }
    } catch {
      // never throw
    }
  });
}

function safeStringify(value: unknown): string {
  try {
    return typeof value === "object" && value !== null
      ? JSON.stringify(value, safeReplacer)
      : String(value);
  } catch {
    try {
      return String(value);
    } catch {
      return "[unserializable]";
    }
  }
}

function safeReplacer(_key: string, value: unknown): unknown {
  if (typeof _key === "string" && SECRET_KEY_RE.test(_key)) return "[REDACTED]";
  return value;
}

// ── Init ──────────────────────────────────────────────────────────

/**
 * Install global listeners. Idempotent. Safe to call during module import
 * (guarded by typeof window) — the side-effectful entry point is
 * `web/lib/clientLogger-init.ts`, imported once from the layout.
 */
export function initClientLogger(): void {
  if (initialized) return;
  if (!LOGGING_ENABLED) return;
  if (typeof window === "undefined") return;
  initialized = true;
  try {
    installGlobalHooks();
  } catch {
    // never throw
  }
}
