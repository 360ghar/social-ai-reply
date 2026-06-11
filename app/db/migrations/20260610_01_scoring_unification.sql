-- Scoring unification + scan progress + intent ladder columns.
-- Idempotent; apply via Supabase SQL editor or psql.

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS scoring_breakdown JSONB DEFAULT '{}'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS buying_stage TEXT;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS intent_confidence REAL;

CREATE INDEX IF NOT EXISTS idx_opportunities_buying_stage
    ON opportunities (project_id, buying_stage);

-- Incremental scan progress for the polling UI.
ALTER TABLE scan_runs ADD COLUMN IF NOT EXISTS subreddits_total INT DEFAULT 0;
ALTER TABLE scan_runs ADD COLUMN IF NOT EXISTS subreddits_scanned INT DEFAULT 0;
