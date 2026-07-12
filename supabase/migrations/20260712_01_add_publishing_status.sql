-- Add 'publishing' as an intermediate status for atomic claim-before-publish
alter type suggestion_status add value if not exists 'publishing';
