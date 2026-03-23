from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import app
from app.db.session import get_db
from app.services.product.reddit import RedditPost, RedditSubredditMatch


def setup_db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return session_local()


def test_v1_auth_project_and_brand_flow():
    db = setup_db()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    register = client.post(
        "/v1/auth/register",
        json={
            "email": "founder@example.com",
            "password": "strongpass123",
            "full_name": "Founder",
            "workspace_name": "Growth Ops",
        },
    )
    assert register.status_code == 201
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project = client.post("/v1/projects", json={"name": "Launch Project", "description": "Primary GTM motion"}, headers=headers)
    assert project.status_code == 201
    project_id = project.json()["id"]

    brand = client.put(
        f"/v1/brand/{project_id}",
        json={
            "brand_name": "RedditFlow",
            "website_url": "https://example.com",
            "summary": "Hosted Reddit opportunity intelligence for SaaS teams.",
            "voice_notes": "Specific and practical",
            "product_summary": "Find threads and write better replies.",
            "target_audience": "founders, growth marketers",
            "call_to_action": "Offer the process when invited.",
            "reddit_username": "redditflow",
            "linkedin_url": "https://linkedin.com/company/redditflow",
        },
        headers=headers,
    )
    assert brand.status_code == 200
    assert brand.json()["brand_name"] == "RedditFlow"

    prompts = client.get(f"/v1/prompts?project_id={project_id}", headers=headers)
    assert prompts.status_code == 200
    assert len(prompts.json()) >= 3

    app.dependency_overrides.clear()


def test_v1_discovery_scan_and_draft_flow(monkeypatch):
    db = setup_db()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    register = client.post(
        "/v1/auth/register",
        json={
            "email": "ops@example.com",
            "password": "strongpass123",
            "full_name": "Ops Lead",
            "workspace_name": "Signals",
        },
    )
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project = client.post("/v1/projects", json={"name": "Signal Project", "description": "Reddit growth"}, headers=headers)
    project_id = project.json()["id"]

    client.put(
        f"/v1/brand/{project_id}",
        json={
            "brand_name": "Signal Project",
            "website_url": "https://example.com",
            "summary": "Find the highest intent Reddit threads.",
            "voice_notes": "Helpful and direct",
            "product_summary": "Scoring and drafting for Reddit engagement.",
            "target_audience": "founders, marketers",
            "call_to_action": "Offer the scoring rubric if useful.",
            "reddit_username": "signalproject",
            "linkedin_url": "https://linkedin.com/company/signalproject",
        },
        headers=headers,
    )

    client.post(
        f"/v1/personas?project_id={project_id}",
        json={
            "name": "Founder",
            "role": "Founder",
            "summary": "Wants repeatable, non-spammy demand capture.",
            "pain_points": ["Low signal outreach"],
            "goals": ["Capture intent"],
            "triggers": ["Pipeline softness"],
            "preferred_subreddits": ["saas"],
            "source": "manual",
            "is_active": True,
        },
        headers=headers,
    )

    keywords = client.post(f"/v1/discovery/keywords/generate?project_id={project_id}", json={"count": 6}, headers=headers)
    assert keywords.status_code == 200
    assert keywords.json()

    monkeypatch.setattr(
        "app.api.v1.routes.RedditClient.search_subreddits",
        lambda self, keyword, limit=10: [
            RedditSubredditMatch(name="saas", title="SaaS", description="Software founders discussing growth", subscribers=120000)
        ],
    )
    monkeypatch.setattr(
        "app.api.v1.routes.RedditClient.subreddit_rules",
        lambda self, name: ["No self-promo", "Explain your reasoning"],
    )
    monkeypatch.setattr(
        "app.api.v1.routes.RedditClient.subreddit_about",
        lambda self, name: {"title": "SaaS", "public_description": "Software founders discussing growth", "subscribers": 120000},
    )
    monkeypatch.setattr(
        "app.api.v1.routes.RedditClient.search_posts",
        lambda self, subreddit, keywords, limit=20, sort="new": [
            RedditPost(
                post_id="abc123",
                subreddit=subreddit,
                title="How do founders find non-spammy demand capture?",
                author="maker1",
                permalink="https://reddit.com/r/saas/comments/abc123",
                body="Looking for a better way to find relevant threads without blasting replies.",
                created_at=datetime.now(timezone.utc),
                num_comments=8,
                score=42,
            )
        ],
    )

    subreddits = client.post(
        f"/v1/discovery/subreddits/discover?project_id={project_id}",
        json={"max_subreddits": 5},
        headers=headers,
    )
    assert subreddits.status_code == 200
    assert subreddits.json()[0]["name"] == "saas"

    scan = client.post(
        "/v1/scans",
        json={"project_id": project_id, "search_window_hours": 72, "max_posts_per_subreddit": 10},
        headers=headers,
    )
    assert scan.status_code == 200
    assert scan.json()["status"] == "completed"

    opportunities = client.get(f"/v1/opportunities?project_id={project_id}", headers=headers)
    assert opportunities.status_code == 200
    assert opportunities.json()
    opportunity_id = opportunities.json()[0]["id"]

    draft = client.post("/v1/drafts/replies", json={"opportunity_id": opportunity_id}, headers=headers)
    assert draft.status_code == 201
    assert "practical" in draft.json()["content"].lower()

    app.dependency_overrides.clear()
