-- ROI attribution: tracked links + click logging.
-- Idempotent; apply via Supabase SQL editor or psql.

CREATE TABLE IF NOT EXISTS tracked_links (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    code TEXT UNIQUE NOT NULL,
    destination_url TEXT NOT NULL,
    opportunity_id INT NULL,
    reply_draft_id INT NULL,
    utm_params JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS link_clicks (
    id SERIAL PRIMARY KEY,
    tracked_link_id INT REFERENCES tracked_links(id) ON DELETE CASCADE,
    clicked_at TIMESTAMPTZ DEFAULT NOW(),
    referrer TEXT,
    user_agent_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_tracked_links_project_id
    ON tracked_links (project_id);

CREATE INDEX IF NOT EXISTS idx_tracked_links_code
    ON tracked_links (code);

CREATE INDEX IF NOT EXISTS idx_link_clicks_tracked_link_id
    ON link_clicks (tracked_link_id);
