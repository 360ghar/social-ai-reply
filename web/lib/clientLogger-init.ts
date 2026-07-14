/**
 * Side-effectful entry point for the client logger.
 *
 * Import this once from the earliest client-side mount (AuthProvider's
 * useEffect) — it installs the global window "error" / "unhandledrejection"
 * listeners and console.error wrapper. Safe to import multiple times
 * (init is idempotent) and safe during SSR (guarded by typeof window).
 *
 * Kept as a separate module so the layout (a Server Component) can pull it
 * in via a client component import without bundling the whole logger into
 * every server-rendered page.
 */
"use client";

import { initClientLogger } from "./clientLogger";

initClientLogger();
