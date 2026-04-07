"""API smoke tests for public app endpoints."""

from sqlalchemy import create_engine, inspect, text

from app.main import _migrate_auth_schema


def test_health_endpoint(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["checks"]["api"] == "ok"
    assert resp.json()["checks"]["database"] == "ok"


def test_ready_endpoint(client):
    resp = client.get("/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    assert resp.json()["checks"]["api"] == "ok"
    assert resp.json()["checks"]["database"] == "ok"


def test_startup_migration_adds_legacy_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")

    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE account_users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE brand_profiles (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                brand_name VARCHAR(255) NOT NULL,
                website_url VARCHAR(1024),
                summary TEXT,
                voice_notes TEXT,
                product_summary TEXT,
                target_audience TEXT,
                call_to_action TEXT,
                reddit_username VARCHAR(255),
                linkedin_url VARCHAR(1024),
                last_analyzed_at DATETIME,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        ))
        conn.execute(text("CREATE TABLE password_reset_tokens (id INTEGER PRIMARY KEY)"))

    _migrate_auth_schema(engine)

    inspector = inspect(engine)
    account_user_columns = {column["name"] for column in inspector.get_columns("account_users")}
    brand_profile_columns = {column["name"] for column in inspector.get_columns("brand_profiles")}

    assert "supabase_user_id" in account_user_columns
    assert "password_hash" in account_user_columns
    assert "tokens_invalid_before" in account_user_columns
    assert "revoked_access_token_hash" in account_user_columns
    assert "business_domain" in brand_profile_columns
    assert "password_reset_tokens" not in inspector.get_table_names()
