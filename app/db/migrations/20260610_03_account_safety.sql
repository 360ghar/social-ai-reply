-- Account-safety copilot columns for connected Reddit accounts.
-- Idempotent; apply via Supabase SQL editor or psql.

ALTER TABLE reddit_accounts ADD COLUMN IF NOT EXISTS karma INT;
ALTER TABLE reddit_accounts ADD COLUMN IF NOT EXISTS account_created_at TIMESTAMPTZ;
ALTER TABLE reddit_accounts ADD COLUMN IF NOT EXISTS safety_config JSONB DEFAULT '{}'::jsonb;
ALTER TABLE reddit_accounts ADD COLUMN IF NOT EXISTS last_safety_check_at TIMESTAMPTZ;
ALTER TABLE reddit_accounts ADD COLUMN IF NOT EXISTS shadowban_suspected BOOLEAN DEFAULT FALSE;
