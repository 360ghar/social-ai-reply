-- ============================================================================
-- Align auto_pipelines schema with application code
-- ============================================================================
-- Date:     2026-04-15
-- Author:   RedditFlow engineering (applied during pedantic-mirzakhani PR)
-- Concern:  The `auto_pipelines` table was originally defined as a recurring
--           pipeline CONFIG (config_json / last_run_at / next_run_at). The
--           application code now treats each row as one individual pipeline
--           RUN, with progress tracking, per-step state, and per-run counts.
--           The code drifted ahead of the schema; this migration realigns it.
--
--           Before this migration, POST /v1/auto-pipeline/run returned a
--           Starlette 500 with the postgrest error:
--             PGRST204: Could not find the 'current_step' column of
--             'auto_pipelines' in the schema cache
--           because app/api/v1/routes/auto_pipeline.py:54 and
--           app/services/product/pipeline.py were inserting/updating 12
--           columns that didn't exist in the DB.
--
-- Safety:   Non-destructive and idempotent. All ADD COLUMN statements use
--           IF NOT EXISTS, so re-running this migration is a no-op. No
--           existing column is renamed, retyped, or dropped. No data is
--           modified. The original columns (config_json, last_run_at,
--           next_run_at) are left in place — they are unused by the new
--           run-record model but are harmless to keep for now, and keeping
--           them avoids coupling this migration with application-layer
--           changes that would remove their references.
-- ============================================================================

ALTER TABLE auto_pipelines
    ADD COLUMN IF NOT EXISTS website_url          TEXT,
    ADD COLUMN IF NOT EXISTS progress             INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS current_step         TEXT,
    ADD COLUMN IF NOT EXISTS started_at           TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS completed_at         TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS brand_summary        TEXT,
    ADD COLUMN IF NOT EXISTS personas_generated   INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS keywords_generated   INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS subreddits_found     INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS opportunities_found  INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS drafts_generated     INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS error_message        TEXT;

-- PostgREST caches the schema shape. Without an explicit reload, the
-- client still sees the old shape and the INSERT fails with PGRST204 even
-- after the columns are present. Supabase auto-reloads on DDL, but we
-- notify explicitly so this migration is hermetic.
NOTIFY pgrst, 'reload schema';
