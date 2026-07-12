-- Add claim_token for per-worker ownership tracking during publish
alter table tweet_suggestions add column if not exists claim_token text;
