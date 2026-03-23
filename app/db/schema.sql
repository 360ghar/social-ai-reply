-- PostgreSQL-oriented schema reference for production deployments.

CREATE TABLE IF NOT EXISTS target_keywords (
    id SERIAL PRIMARY KEY,
    business_input VARCHAR(255) NOT NULL,
    keyword VARCHAR(255) NOT NULL,
    profile_type VARCHAR(255) NOT NULL,
    overlap_reason TEXT NOT NULL,
    priority_score INTEGER NOT NULL DEFAULT 50,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_keyword_business_type UNIQUE (business_input, keyword, profile_type)
);
CREATE INDEX IF NOT EXISTS ix_target_keywords_business_input ON target_keywords (business_input);
CREATE INDEX IF NOT EXISTS ix_target_keywords_keyword ON target_keywords (keyword);

CREATE TABLE IF NOT EXISTS target_profiles (
    id SERIAL PRIMARY KEY,
    instagram_user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    bio TEXT,
    followers_count INTEGER NOT NULL DEFAULT 0,
    following_count INTEGER NOT NULL DEFAULT 0,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_scraped_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_target_profiles_instagram_user_id ON target_profiles (instagram_user_id);
CREATE INDEX IF NOT EXISTS ix_target_profiles_username ON target_profiles (username);

CREATE TABLE IF NOT EXISTS profile_keyword_map (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES target_keywords(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_profile_keyword UNIQUE (profile_id, keyword_id)
);
CREATE INDEX IF NOT EXISTS ix_profile_keyword_profile_id ON profile_keyword_map (profile_id);
CREATE INDEX IF NOT EXISTS ix_profile_keyword_keyword_id ON profile_keyword_map (keyword_id);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    instagram_user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    follower_count INTEGER NOT NULL DEFAULT 0,
    following_count INTEGER NOT NULL DEFAULT 0,
    profile_pic_url VARCHAR(1024),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_instagram_user_id ON users (instagram_user_id);
CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);

CREATE TYPE interaction_type AS ENUM ('follower', 'following', 'like', 'comment');

CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    event_key VARCHAR(255) NOT NULL UNIQUE,
    target_profile_id INTEGER NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    interaction_type interaction_type NOT NULL,
    media_id BIGINT,
    comment_text TEXT,
    interacted_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_interactions_target_profile_id ON interactions (target_profile_id);
CREATE INDEX IF NOT EXISTS ix_interactions_user_id ON interactions (user_id);
CREATE INDEX IF NOT EXISTS ix_interactions_interaction_type ON interactions (interaction_type);
CREATE INDEX IF NOT EXISTS ix_interactions_scraped_at ON interactions (scraped_at);
CREATE INDEX IF NOT EXISTS ix_interactions_user_target_type ON interactions (user_id, target_profile_id, interaction_type);
CREATE INDEX IF NOT EXISTS ix_interactions_target_type ON interactions (target_profile_id, interaction_type);

CREATE TYPE crawl_status AS ENUM ('queued', 'running', 'completed', 'failed');

CREATE TABLE IF NOT EXISTS crawl_runs (
    id UUID PRIMARY KEY,
    status crawl_status NOT NULL DEFAULT 'queued',
    business_input VARCHAR(255) NOT NULL,
    target_profiles_goal INTEGER NOT NULL DEFAULT 1000,
    profiles_discovered INTEGER NOT NULL DEFAULT 0,
    interactions_collected INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_crawl_runs_status ON crawl_runs (status);
CREATE INDEX IF NOT EXISTS ix_crawl_runs_business_input ON crawl_runs (business_input);
