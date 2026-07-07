-- ============================================================================
-- Manual publishing fallback tracking
-- ============================================================================
-- Lets approved calendar posts move to a completed state before OAuth/API
-- publishing is available. This supports the zero-cost MVP flow:
-- approve -> copy/open platform -> mark published.
-- ============================================================================

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ NULL;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS published_url TEXT NULL;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS publish_mode TEXT NULL;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS publish_error TEXT NULL;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS publish_note TEXT NULL;

ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS last_publish_attempt_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_post_drafts_project_publish_state
    ON post_drafts(project_id, status, published_at);
