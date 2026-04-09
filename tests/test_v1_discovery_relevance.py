from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker

from app.db.models import MonitoredSubreddit, Project
from app.services.product.copilot import GeneratedKeyword, WebsiteAnalysis
from app.services.product.discovery import discover_and_store_subreddits
from app.services.product.reddit import RedditPost, RedditSubredditMatch


def _create_project(client, name: str = "Signal Project") -> int:
    project = client.post("/v1/projects", json={"name": name, "description": "Reddit growth"})
    assert project.status_code == 201
    return project.json()["id"]


def _configure_brand_and_persona(client, project_id: int) -> None:
    brand = client.put(
        f"/v1/brand/{project_id}",
        json={
            "brand_name": "SignalFlow",
            "website_url": "https://example.com",
            "summary": "Find the highest intent Reddit threads for SaaS teams.",
            "voice_notes": "Helpful and direct",
            "product_summary": "Discover relevant Reddit conversations and draft grounded replies.",
            "target_audience": "founders, growth marketers",
            "call_to_action": "Offer the scoring rubric if useful.",
            "reddit_username": "signalflow",
            "linkedin_url": "https://linkedin.com/company/signalflow",
        },
    )
    assert brand.status_code == 200

    persona = client.post(
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
    )
    assert persona.status_code == 201


def _configure_real_estate_brand(client, project_id: int) -> None:
    brand = client.put(
        f"/v1/brand/{project_id}",
        json={
            "brand_name": "360Ghar",
            "website_url": "https://360ghar.com",
            "summary": "AI-powered real estate marketplace for home buyers and renters.",
            "voice_notes": "Helpful and direct",
            "product_summary": "Compare property listings, apartments, rent options, and home tours.",
            "target_audience": "home buyers, renters, real estate agents",
            "call_to_action": "Offer practical next steps for evaluating listings.",
            "reddit_username": "360ghar",
            "linkedin_url": "https://linkedin.com/company/360ghar",
        },
    )
    assert brand.status_code == 200


def _mock_subreddit_search(self, keyword, limit=10):
    return [
        RedditSubredditMatch(
            name="hbo",
            title="HBO",
            description="TV shows and episode discussion",
            subscribers=500000,
        ),
        RedditSubredditMatch(
            name="saas",
            title="SaaS",
            description="Software founders discussing growth",
            subscribers=120000,
        ),
    ]


def _mock_subreddit_about(self, name):
    if name == "saas":
        return {
            "title": "SaaS",
            "public_description": "Software founders discussing growth and demand capture",
            "subscribers": 120000,
        }
    return {
        "title": "HBO",
        "public_description": "TV shows, episodes, and streaming discussion",
        "subscribers": 500000,
    }


def _mock_subreddit_rules(self, name):
    return ["No self-promo", "Explain your reasoning"] if name == "saas" else ["Stay on topic"]


def _mock_subreddit_posts(self, name, sort="hot", limit=6):
    if name == "saas":
        return [
            RedditPost(
                post_id="s1",
                subreddit="saas",
                title="How do founders find high-intent Reddit threads?",
                author="founder1",
                permalink="https://reddit.com/r/saas/s1",
                body="Looking for a better demand capture workflow.",
                created_at=datetime.now(UTC),
                num_comments=4,
                score=12,
            )
        ]
    return [
        RedditPost(
            post_id="h1",
            subreddit="hbo",
            title="Best HBO episode this season?",
            author="viewer1",
            permalink="https://reddit.com/r/hbo/h1",
            body="Looking for streaming recommendations.",
            created_at=datetime.now(UTC),
            num_comments=50,
            score=120,
        )
    ]


def _mock_search_posts(self, subreddit, keywords, limit=20, sort="new"):
    return [
        RedditPost(
            post_id=f"{subreddit}-good",
            subreddit=subreddit,
            title="How do founders find non-spammy demand capture on Reddit?",
            author="maker1",
            permalink=f"https://reddit.com/r/{subreddit}/comments/good",
            body="Looking for tools to discover relevant Reddit threads without blasting generic replies.",
            created_at=datetime.now(UTC),
            num_comments=8,
            score=42,
        ),
        RedditPost(
            post_id=f"{subreddit}-bad",
            subreddit=subreddit,
            title="How do I meal prep faster?",
            author="maker2",
            permalink=f"https://reddit.com/r/{subreddit}/comments/bad",
            body="Need kitchen advice for weekly food prep.",
            created_at=datetime.now(UTC),
            num_comments=6,
            score=17,
        ),
    ]


def test_manual_discovery_filters_offtopic_subreddits_and_posts(authed_client, monkeypatch):
    client, _auth = authed_client
    project_id = _create_project(client)
    _configure_brand_and_persona(client, project_id)
    monkeypatch.setattr(
        "app.services.product.copilot.ProductCopilot.generate_keywords",
        lambda self, brand, personas, count=12: [
            GeneratedKeyword(keyword="demand capture", rationale="High-intent SaaS pain point.", priority_score=92),
            GeneratedKeyword(keyword="reddit threads", rationale="Relevant channel phrase.", priority_score=86),
            GeneratedKeyword(keyword="founders", rationale="Audience phrase.", priority_score=65),
        ],
    )

    keywords = client.post(f"/v1/discovery/keywords/generate?project_id={project_id}", json={"count": 6})
    assert keywords.status_code == 200
    assert keywords.json()

    monkeypatch.setattr("app.services.product.reddit.RedditClient.search_subreddits", _mock_subreddit_search)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.subreddit_about", _mock_subreddit_about)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.subreddit_rules", _mock_subreddit_rules)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.list_subreddit_posts", _mock_subreddit_posts)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.search_posts", _mock_search_posts)

    subreddits = client.post(
        f"/v1/discovery/subreddits/discover?project_id={project_id}",
        json={"max_subreddits": 5},
    )
    assert subreddits.status_code == 200
    assert [row["name"] for row in subreddits.json()] == ["saas"]

    scan = client.post(
        "/v1/scans",
        json={"project_id": project_id, "search_window_hours": 72, "max_posts_per_subreddit": 10},
    )
    assert scan.status_code == 200
    assert scan.json()["status"] == "completed"

    opportunities = client.get(f"/v1/opportunities?project_id={project_id}")
    assert opportunities.status_code == 200
    titles = [row["title"] for row in opportunities.json()]
    assert titles == ["How do founders find non-spammy demand capture on Reddit?"]


def test_scan_uses_domain_filtered_keywords_for_real_estate_projects(authed_client, db_session, monkeypatch):
    client, _auth = authed_client
    project_id = _create_project(client, name="360Ghar")
    _configure_real_estate_brand(client, project_id)

    for keyword, priority in [
        ("real", 95),
        ("vr", 92),
        ("ai", 90),
        ("property listings", 88),
        ("real estate marketplace", 84),
        ("home buyers", 82),
    ]:
        response = client.post(
            f"/v1/discovery/keywords?project_id={project_id}",
            json={"keyword": keyword, "rationale": "test", "priority_score": priority, "is_active": True},
        )
        assert response.status_code == 201

    db_session.add(
        MonitoredSubreddit(
            project_id=project_id,
            name="realestate",
            title="Real Estate",
            description="Property buying, renting, and apartment discussions.",
            subscribers=75000,
            activity_score=70,
            fit_score=82,
            is_active=True,
        )
    )
    db_session.commit()

    captured_keywords: list[list[str]] = []

    def _capture_real_estate_search(self, subreddit, keywords, limit=20, sort="new"):
        captured_keywords.append(list(keywords))
        return [
            RedditPost(
                post_id=f"{subreddit}-good",
                subreddit=subreddit,
                title="How do home buyers compare property listings before booking tours?",
                author="buyer1",
                permalink=f"https://reddit.com/r/{subreddit}/comments/good",
                body="Looking for advice on apartments, rent options, and what to verify in a real estate listing.",
                created_at=datetime.now(UTC),
                num_comments=7,
                score=31,
            ),
            RedditPost(
                post_id=f"{subreddit}-bad",
                subreddit=subreddit,
                title="Which VR headset is best for gaming?",
                author="gamer1",
                permalink=f"https://reddit.com/r/{subreddit}/comments/bad",
                body="Looking for AI upscaling and better graphics performance.",
                created_at=datetime.now(UTC),
                num_comments=5,
                score=19,
            ),
        ]

    monkeypatch.setattr("app.services.product.reddit.RedditClient.search_posts", _capture_real_estate_search)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.subreddit_rules", lambda self, name: [])

    scan = client.post(
        "/v1/scans",
        json={"project_id": project_id, "search_window_hours": 72, "max_posts_per_subreddit": 10},
    )
    assert scan.status_code == 200
    assert captured_keywords
    assert "real" not in captured_keywords[0]
    assert "vr" not in captured_keywords[0]
    assert "ai" not in captured_keywords[0]
    assert "property listings" in captured_keywords[0]
    assert "home buyers" in captured_keywords[0]

    opportunities = client.get(f"/v1/opportunities?project_id={project_id}")
    assert opportunities.status_code == 200
    titles = [row["title"] for row in opportunities.json()]
    assert titles == ["How do home buyers compare property listings before booking tours?"]


def test_auto_pipeline_uses_shared_relevance_filters(authed_client, db_session, monkeypatch):
    client, _auth = authed_client
    session_factory = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr("app.services.product.pipeline.SessionLocal", session_factory)

    monkeypatch.setattr(
        "app.services.product.copilot.ProductCopilot.analyze_website",
        lambda self, website_url: WebsiteAnalysis(
            brand_name="SignalFlow",
            summary="High-intent Reddit thread discovery for SaaS teams.",
            product_summary="Discover relevant Reddit conversations and draft grounded replies.",
            target_audience="founders, growth marketers",
            call_to_action="Offer the workflow if invited.",
            voice_notes="Helpful and direct.",
        ),
    )
    monkeypatch.setattr(
        "app.services.product.copilot.ProductCopilot.suggest_personas",
        lambda self, brand, count=4: [
            {
                "name": "Founder",
                "role": "Founder",
                "summary": "Needs repeatable, high-signal demand capture.",
                "pain_points": ["Low signal outreach"],
                "goals": ["Find relevant conversations"],
                "triggers": ["Pipeline softness"],
                "preferred_subreddits": ["saas"],
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.product.copilot.ProductCopilot.generate_reply",
        lambda self, opportunity, brand, prompts: ("Helpful draft", "Reasonable rationale", "Prompt source"),
    )
    monkeypatch.setattr(
        "app.services.product.copilot.ProductCopilot.generate_keywords",
        lambda self, brand, personas, count=15: [
            GeneratedKeyword(keyword="demand capture", rationale="High-intent SaaS pain point.", priority_score=92),
            GeneratedKeyword(keyword="reddit threads", rationale="Relevant channel phrase.", priority_score=86),
            GeneratedKeyword(keyword="founders", rationale="Audience phrase.", priority_score=65),
        ],
    )
    monkeypatch.setattr("app.services.product.reddit.RedditClient.search_subreddits", _mock_subreddit_search)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.subreddit_about", _mock_subreddit_about)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.subreddit_rules", _mock_subreddit_rules)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.list_subreddit_posts", _mock_subreddit_posts)
    monkeypatch.setattr("app.services.product.reddit.RedditClient.search_posts", _mock_search_posts)

    start = client.post("/v1/auto-pipeline/run", json={"website_url": "https://example.com"})
    assert start.status_code == 200
    pipeline_id = start.json()["id"]

    pipeline = client.get(f"/v1/auto-pipeline/{pipeline_id}")
    assert pipeline.status_code == 200
    data = pipeline.json()
    assert data["status"] == "ready"
    assert [row["name"] for row in data["results"]["subreddits"]] == ["saas"]
    assert data["drafts_count"] == 1
    assert [row["opportunity_title"] for row in data["results"]["drafts"]] == [
        "How do founders find non-spammy demand capture on Reddit?"
    ]


def test_discovery_deduplicates_candidates_before_detail_fetch(authed_client, db_session):
    client, _auth = authed_client
    project_id = _create_project(client, name="Fast Discovery")
    _configure_brand_and_persona(client, project_id)

    for keyword, priority in [
        ("founders", 90),
        ("demand capture", 85),
        ("reddit threads", 80),
    ]:
        response = client.post(
            f"/v1/discovery/keywords?project_id={project_id}",
            json={"keyword": keyword, "rationale": "test", "priority_score": priority, "is_active": True},
        )
        assert response.status_code == 201

    project = db_session.get(Project, project_id)

    class CountingRedditClient:
        def __init__(self):
            self.search_calls = 0
            self.posts_calls = 0
            self.rules_calls = 0

        def search_subreddits(self, keyword, limit=10):
            self.search_calls += 1
            return [
                RedditSubredditMatch(
                    name="hbo",
                    title="HBO",
                    description="TV shows and episode discussion",
                    subscribers=500000,
                ),
                RedditSubredditMatch(
                    name="saas",
                    title="SaaS",
                    description="Software founders discussing growth",
                    subscribers=120000,
                ),
            ]

        def subreddit_about(self, name):
            raise AssertionError("discover_and_store_subreddits should not call subreddit_about during initial discovery")

        def subreddit_rules(self, name):
            self.rules_calls += 1
            return ["No self-promo", "Explain your reasoning"] if name == "saas" else ["Stay on topic"]

        def list_subreddit_posts(self, name, sort="hot", limit=6):
            self.posts_calls += 1
            if name == "saas":
                return [
                    RedditPost(
                        post_id="s1",
                        subreddit="saas",
                        title="How do founders find high-intent Reddit threads?",
                        author="founder1",
                        permalink="https://reddit.com/r/saas/s1",
                        body="Looking for a better demand capture workflow.",
                        created_at=datetime.now(UTC),
                        num_comments=4,
                        score=12,
                    )
                ]
            return [
                RedditPost(
                    post_id="h1",
                    subreddit="hbo",
                    title="Best HBO episode this season?",
                    author="viewer1",
                    permalink="https://reddit.com/r/hbo/h1",
                    body="Looking for streaming recommendations.",
                    created_at=datetime.now(UTC),
                    num_comments=50,
                    score=120,
                )
            ]

    reddit = CountingRedditClient()
    created = discover_and_store_subreddits(db_session, project, max_subreddits=2, reddit=reddit)

    assert [row.name for row in created] == ["saas"]
    assert reddit.search_calls == 10
    assert reddit.posts_calls == 1
    assert reddit.rules_calls == 1


def test_discovery_prefers_broad_active_domain_subreddits_over_tiny_accidental_matches(authed_client, db_session):
    client, _auth = authed_client
    project_id = _create_project(client, name="360Ghar Discovery")
    _configure_real_estate_brand(client, project_id)

    for keyword, priority in [
        ("property search", 92),
        ("real estate marketplace", 90),
        ("real estate investors", 88),
        ("property buyers", 84),
        ("sellers in gurugram haryana", 80),
    ]:
        response = client.post(
            f"/v1/discovery/keywords?project_id={project_id}",
            json={"keyword": keyword, "rationale": "test", "priority_score": priority, "is_active": True},
        )
        assert response.status_code == 201

    project = db_session.get(Project, project_id)

    class RankingRedditClient:
        def search_subreddits(self, keyword, limit=10):
            return [
                RedditSubredditMatch(
                    name="FloridaRealEstateLaw",
                    title="Florida Real Estate Law",
                    description="Legal issues affecting buyers, sellers, landlords, and real property owners in Florida.",
                    subscribers=262,
                ),
                RedditSubredditMatch(
                    name="RealEstate",
                    title="HomeOwners & Investors",
                    description="Real estate investing, mortgages, home buying, selling, and renting discussion.",
                    subscribers=2_474_698,
                ),
                RedditSubredditMatch(
                    name="indianrealestate",
                    title="Indian Real Estate",
                    description="Real estate updates and property discussions in India.",
                    subscribers=99_249,
                ),
            ]

        def subreddit_rules(self, name):
            return []

        def list_subreddit_posts(self, name, sort="hot", limit=6):
            if name == "FloridaRealEstateLaw":
                return [
                    RedditPost(
                        post_id="f1",
                        subreddit=name,
                        title="Can a seller back out after inspection?",
                        author="user1",
                        permalink="https://reddit.com/r/FloridaRealEstateLaw/f1",
                        body="Need Florida legal advice before closing.",
                        created_at=datetime.now(UTC),
                        num_comments=2,
                        score=5,
                    )
                ]
            if name == "indianrealestate":
                return [
                    RedditPost(
                        post_id="i1",
                        subreddit=name,
                        title="How do buyers verify property listings in India?",
                        author="user2",
                        permalink="https://reddit.com/r/indianrealestate/i1",
                        body="Looking for advice on fake listings, apartment tours, and pricing.",
                        created_at=datetime.now(UTC),
                        num_comments=8,
                        score=19,
                    )
                ]
            return [
                RedditPost(
                    post_id="r1",
                    subreddit=name,
                    title="First-time buyer trying to compare property listings",
                    author="user3",
                    permalink="https://reddit.com/r/RealEstate/r1",
                    body="Need help evaluating apartments, rent options, and what to ask before touring.",
                    created_at=datetime.now(UTC),
                    num_comments=12,
                    score=34,
                )
            ]

    created = discover_and_store_subreddits(db_session, project, max_subreddits=2, reddit=RankingRedditClient())

    names = [row.name for row in created]
    assert "RealEstate" in names
    assert "indianrealestate" in names
    assert "FloridaRealEstateLaw" not in names


def test_auto_pipeline_skips_subreddit_discovery_when_project_is_already_seeded(authed_client, db_session, monkeypatch):
    client, _auth = authed_client
    project_id = _create_project(client, name="Seeded Pipeline")
    _configure_brand_and_persona(client, project_id)

    session_factory = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr("app.services.product.pipeline.SessionLocal", session_factory)

    monkeypatch.setattr(
        "app.services.product.pipeline.ProductCopilot.analyze_website",
        lambda self, website_url: WebsiteAnalysis(
            brand_name="SignalFlow",
            summary="High-intent Reddit thread discovery for SaaS teams.",
            product_summary="Discover relevant Reddit conversations and draft grounded replies.",
            target_audience="founders, growth marketers",
            call_to_action="Offer the workflow if invited.",
            voice_notes="Helpful and direct.",
        ),
    )
    monkeypatch.setattr(
        "app.services.product.pipeline.ProductCopilot.suggest_personas",
        lambda self, brand, count=4: [
            {
                "name": "Founder",
                "role": "Founder",
                "summary": "Needs repeatable, high-signal demand capture.",
                "pain_points": ["Low signal outreach"],
                "goals": ["Find relevant conversations"],
                "triggers": ["Pipeline softness"],
                "preferred_subreddits": ["saas"],
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.product.pipeline.ProductCopilot.generate_keywords",
        lambda self, brand, personas, count=15: [
            GeneratedKeyword(keyword="demand capture", rationale="High-intent SaaS pain point.", priority_score=92),
            GeneratedKeyword(keyword="reddit threads", rationale="Relevant channel phrase.", priority_score=86),
        ],
    )
    monkeypatch.setattr(
        "app.services.product.pipeline.discover_and_store_subreddits",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("pipeline should skip subreddit discovery")),
    )
    monkeypatch.setattr(
        "app.services.product.pipeline.run_scan",
        lambda *args, **kwargs: type("ScanRunStub", (), {"opportunities_found": 0})(),
    )

    for idx in range(6):
        db_session.add(
            MonitoredSubreddit(
                project_id=project_id,
                name=f"seeded{idx}",
                title=f"Seeded {idx}",
                description="Pre-seeded subreddit",
                subscribers=5000 + idx,
                activity_score=60,
                fit_score=75,
                is_active=True,
            )
        )
    db_session.commit()

    start = client.post(
        "/v1/auto-pipeline/run",
        json={"website_url": "https://example.com", "project_id": project_id},
    )
    assert start.status_code == 200

    pipeline_id = start.json()["id"]
    pipeline = client.get(f"/v1/auto-pipeline/{pipeline_id}")
    assert pipeline.status_code == 200
    assert pipeline.json()["status"] == "ready"
