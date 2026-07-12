-- Add claimed_at timestamp for tracking in-flight publishing claims
alter table tweet_suggestions add column if not exists claimed_at timestamp with time zone;
