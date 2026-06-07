-- ============================================================================
-- Add platform column to opportunities and score_feedback table
-- ============================================================================
-- Date:     2026-05-20
-- Author:   RedditFlow engineering
-- Concern:  Two missing schema items:
--           1. The `platform` column on `opportunities` is referenced by
--              app/services/product/social_post.py:as_opportunity_dict but
--              does not exist in the DB yet. Without it, multi-platform scans
--              (Twitter, etc.) lose the platform identifier on insert.
--           2. The `score_feedback` table is referenced by
--              app/db/tables/discovery.py (create_score_feedback,
--              list_score_feedback_for_workspace) but has never been created.
--              Score calibration logging is silently lost.
--
-- Safety:   Non-destructive and idempotent. ADD COLUMN IF NOT EXISTS on
--           opportunities. CREATE TABLE IF NOT EXISTS for score_feedback.
--           No existing data is modified or dropped.
-- ============================================================================

-- 1. Add platform column to opportunities (defaults to 'reddit' for
--    existing rows, matching the pre-column behaviour).
ALTER TABLE opportunities
    ADD COLUMN IF NOT EXISTS platform TEXT NOT NULL DEFAULT 'reddit';

-- 2. Create score_feedback table for recording user actions on
--    opportunities (saved / ignored / replied) to enable score
--    calibration over time.
CREATE TABLE IF NOT EXISTS score_feedback (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workspace_id  BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE SET NULL,
    user_id       BIGINT,
    action        TEXT NOT NULL,            -- 'saved', 'ignored', 'replied', etc.
    original_score INTEGER,                 -- opportunity score at action time
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_score_feedback_workspace
    ON score_feedback(workspace_id, created_at DESC);

-- PostgREST schema cache reload.
NOTIFY pgrst, 'reload schema';
