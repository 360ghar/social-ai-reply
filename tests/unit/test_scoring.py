"""Unit tests for post scoring and eligibility gates."""

from datetime import UTC, datetime

from app.services.product.reddit import RedditPost
from app.services.product.scoring import MIN_RELEVANT_OPPORTUNITY_SCORE, score_post


def _make_brand():
    return {
        "id": 1,
        "project_id": 1,
        "brand_name": "SignalFlow",
        "summary": "High-intent Reddit thread discovery for SaaS teams.",
        "product_summary": "Find relevant Reddit conversations and draft grounded replies.",
        "target_audience": "founders, growth marketers",
    }


def _make_real_estate_brand():
    return {
        "id": 2,
        "project_id": 2,
        "brand_name": "360Ghar",
        "summary": "AI-powered real estate marketplace for home buyers and renters.",
        "product_summary": "Compare property listings, apartments, rent options, and home tours.",
        "target_audience": "home buyers, renters, real estate agents",
    }


def _make_subreddit(fit_score: int = 80):
    return {
        "id": 1,
        "project_id": 1,
        "name": "saas",
        "title": "SaaS",
        "description": "Software founders discussing growth and demand capture.",
        "subscribers": 1000,
        "fit_score": fit_score,
    }


def _make_post(**overrides):
    defaults = dict(
        post_id="p1",
        subreddit="saas",
        title="How do founders find non-spammy demand capture on Reddit?",
        author="user1",
        permalink="https://reddit.com/r/saas/p1",
        body="Looking for tools to discover Reddit threads without blasting generic replies.",
        created_at=datetime.now(UTC),
        num_comments=5,
        score=10,
    )
    defaults.update(overrides)
    return RedditPost(**defaults)


class TestScorePost:
    def test_high_intent_topic_match_passes(self):
        result = score_post(
            _make_post(),
            _make_brand(),
            _make_subreddit(),
            ["reddit threads", "demand capture", "non-spammy replies"],
            ["No self-promo", "Explain your reasoning"],
        )

        assert result.eligible is True
        assert result.total >= MIN_RELEVANT_OPPORTUNITY_SCORE
        assert "demand capture" in result.keyword_hits

    def test_help_intent_without_topic_match_fails(self):
        result = score_post(
            _make_post(
                title="How do I improve my sleep schedule?",
                body="Looking for advice on getting better rest every night.",
            ),
            _make_brand(),
            _make_subreddit(),
            ["reddit threads", "demand capture", "non-spammy replies"],
            [],
        )

        assert result.eligible is False
        assert result.total < MIN_RELEVANT_OPPORTUNITY_SCORE
        assert any("topical overlap" in reason.lower() for reason in result.reasons)

    def test_topic_match_without_explicit_ask_stays_eligible_but_flagged(self):
        """A topic-matched post without explicit help-seeking intent is now
        a soft signal (score penalty + warning reason), not a hard rejection.

        Rationale: the previous all-AND gate silently dropped most posts
        Reddit returned, leaving Opportunity feeds empty. Moving intent
        from a hard gate to a soft penalty lets such posts surface so a
        human can decide whether to engage."""
        result = score_post(
            _make_post(
                title="Reddit thread discovery workflow for SaaS teams",
                body="Our team built a repeatable demand capture process last quarter.",
            ),
            _make_brand(),
            _make_subreddit(),
            ["reddit thread discovery", "demand capture", "saas teams"],
            [],
        )

        # Post is eligible (topic + domain pass), but flagged for the
        # missing intent signal so the reviewer knows what to expect.
        assert result.eligible is True
        assert any(
            "help-seeking" in reason.lower() or "no explicit help-seeking" in reason.lower()
            for reason in result.reasons
        )

    def test_direct_brand_mention_bypasses_intent_gate(self):
        result = score_post(
            _make_post(
                title="SignalFlow rollout notes from our pilot",
                body="We used SignalFlow to review conversations internally this week.",
            ),
            _make_brand(),
            _make_subreddit(),
            ["reddit thread discovery", "demand capture"],
            [],
        )

        assert result.eligible is True
        assert result.total >= MIN_RELEVANT_OPPORTUNITY_SCORE
        assert "signalflow" in result.keyword_hits

    def test_ambiguous_tech_terms_do_not_pass_real_estate_domain_gate(self):
        result = score_post(
            _make_post(
                subreddit="realestate",
                title="Which VR headset should I buy for gaming?",
                body="Looking for AI features and better graphics performance.",
            ),
            _make_real_estate_brand(),
            _make_subreddit(),
            ["real", "vr", "ai", "property listings", "home buyers"],
            [],
        )

        assert result.eligible is False
        assert result.total < MIN_RELEVANT_OPPORTUNITY_SCORE
        assert any("domain-specific overlap" in reason.lower() for reason in result.reasons)

    def test_multiword_keywords_do_not_match_on_single_role_token_and_stopwords(self):
        result = score_post(
            _make_post(
                subreddit="realestate",
                title="What should sellers disclose before listing in Florida?",
                body="Looking for legal guidance before putting a house on the market.",
            ),
            _make_real_estate_brand(),
            _make_subreddit(),
            ["sellers in gurugram", "real estate marketplace"],
            [],
        )

        assert "sellers in gurugram" not in result.keyword_hits
