-- Partial index for efficient lookup of stale publishing claims
create index if not exists idx_tweet_suggestions_claimed_at_publishing on tweet_suggestions(claimed_at) where status = 'publishing';
