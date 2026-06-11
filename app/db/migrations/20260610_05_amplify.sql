-- ============================================================================
-- Amplification engine: Reddit reply -> X thread / LinkedIn post
-- ============================================================================
-- Date:     2026-06-10
-- Author:   RedditFlow engineering
-- Concern:  post_drafts only supported Reddit posts. The amplification engine
--           repurposes reply drafts / opportunities into X threads and
--           LinkedIn posts, so post_drafts needs a platform discriminator,
--           a thread payload, lineage columns back to the source content,
--           and a status for publish tracking. published_posts needs a
--           platform discriminator + external id for non-Reddit publishes.
--
-- Safety:   Non-destructive and idempotent. ADD COLUMN IF NOT EXISTS only;
--           no existing data is modified or dropped.
-- ============================================================================

-- 1. Platform discriminator for post drafts ('reddit' | 'x' | 'linkedin').
ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT 'reddit';

-- 2. Ordered tweet texts for X threads (empty for non-thread drafts).
ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS thread_json JSONB DEFAULT '[]'::jsonb;

-- 3. Lineage: the reply draft this amplified draft was derived from.
ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS source_reply_draft_id INT NULL;

-- 4. Lineage: the opportunity this amplified draft was derived from.
ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS source_opportunity_id INT NULL;

-- 5. Publish tracking ('draft' | 'posted').
ALTER TABLE post_drafts
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft';

-- 6. published_posts: platform discriminator for non-Reddit publishes.
ALTER TABLE published_posts
    ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT 'reddit';

-- 7. published_posts: external platform id (e.g. tweet id).
ALTER TABLE published_posts
    ADD COLUMN IF NOT EXISTS external_id TEXT NULL;
