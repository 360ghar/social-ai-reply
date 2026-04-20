from app.db.tables.discovery import create_opportunity, get_opportunity_by_id


def test_create_opportunity_populates_legacy_and_current_subreddit_fields(mock_supabase):
    opportunity = create_opportunity(
        mock_supabase,
        {
            "project_id": 1,
            "reddit_post_id": "abc123",
            "subreddit_name": "saas",
            "author": "founder42",
            "title": "How do you find SaaS leads on Reddit?",
            "permalink": "https://reddit.com/r/saas/comments/abc123/test",
            "score": 91,
            "status": "new",
        },
    )

    stored = mock_supabase.table("opportunities").select("*").eq("id", opportunity["id"]).execute().data[0]

    assert opportunity["subreddit_name"] == "saas"
    assert opportunity["subreddit"] == "saas"
    assert stored["subreddit_name"] == "saas"
    assert stored["subreddit"] == "saas"


def test_get_opportunity_by_id_normalizes_legacy_subreddit_field(mock_supabase):
    stored = mock_supabase.table("opportunities").insert(
        {
            "project_id": 1,
            "reddit_post_id": "legacy123",
            "subreddit": "realestate",
            "author": "agent1",
            "title": "Need help validating a listing",
            "permalink": "https://reddit.com/r/realestate/comments/legacy123/test",
            "score": 82,
            "status": "new",
        }
    ).execute().data[0]

    opportunity = get_opportunity_by_id(mock_supabase, stored["id"])

    assert opportunity is not None
    assert opportunity["subreddit"] == "realestate"
    assert opportunity["subreddit_name"] == "realestate"
