-- ============================================================================
-- Voice profiles + subreddit tone rules
-- ============================================================================
-- Date:     2026-06-10
-- Author:   RedditFlow engineering
-- Concern:  Reply drafts currently share one global voice. This adds:
--           1. A `voice_profiles` table so each project can define reusable
--              writing voices (example replies, tone descriptors, banned
--              phrases, an LLM-distilled style guide, and a default flag).
--           2. A `tone_rules` column on `monitored_subreddits` so per-
--              subreddit tone guidance can be injected into reply generation.
--
-- Safety:   Non-destructive and idempotent. CREATE TABLE IF NOT EXISTS for
--           voice_profiles, ADD COLUMN IF NOT EXISTS on monitored_subreddits.
--           No existing data is modified or dropped.
-- ============================================================================

-- 1. Voice profiles per project.
CREATE TABLE IF NOT EXISTS voice_profiles (
    id               SERIAL PRIMARY KEY,
    project_id       INT REFERENCES projects(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    example_replies  JSONB DEFAULT '[]',
    tone_descriptors JSONB DEFAULT '[]',
    banned_phrases   JSONB DEFAULT '[]',
    style_guide      TEXT,
    is_default       BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_profiles_project
    ON voice_profiles(project_id, is_default);

-- 2. Per-subreddit tone rules consumed by reply generation.
ALTER TABLE monitored_subreddits
    ADD COLUMN IF NOT EXISTS tone_rules TEXT;

-- PostgREST schema cache reload.
NOTIFY pgrst, 'reload schema';
