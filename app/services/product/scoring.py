from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.saas_models import BrandProfile, MonitoredSubreddit
from app.services.product.reddit import RedditPost


@dataclass
class OpportunityScore:
    total: int
    keyword_hits: list[str]
    reasons: list[str]
    rule_risk: list[str]


def score_post(
    post: RedditPost,
    brand_profile: BrandProfile | None,
    subreddit: MonitoredSubreddit | None,
    keywords: list[str],
    subreddit_rules: list[str],
) -> OpportunityScore:
    text = f"{post.title} {post.body}".lower()
    keyword_hits = [keyword for keyword in keywords if keyword.lower() in text]
    reasons: list[str] = []
    rule_risk: list[str] = []
    score = 0

    if keyword_hits:
        score += min(35, 12 + len(keyword_hits) * 7)
        reasons.append(f"{len(keyword_hits)} keyword hit(s) matched the post content.")

    intent_phrases = ["how do", "how can", "looking for", "recommend", "best way", "struggling", "any advice"]
    if any(phrase in text for phrase in intent_phrases):
        score += 20
        reasons.append("The post shows explicit help-seeking or recommendation intent.")

    age_hours = max((datetime.now(timezone.utc) - post.created_at).total_seconds() / 3600, 0.0)
    if age_hours <= 12:
        score += 15
        reasons.append("Fresh thread with a high chance of timely engagement.")
    elif age_hours <= 48:
        score += 8
        reasons.append("Recent thread that still has room for relevant replies.")

    if post.num_comments <= 20:
        score += 10
        reasons.append("Low competition thread with space for a visible reply.")
    elif post.num_comments >= 100:
        score -= 5
        reasons.append("Busy thread with heavier reply competition.")

    if subreddit:
        score += min(subreddit.fit_score // 4, 15)
        if subreddit.rules_summary:
            rule_risk.append("Review subreddit rules before posting.")

    if brand_profile and brand_profile.target_audience:
        audience_terms = [term.strip().lower() for term in brand_profile.target_audience.split(",") if term.strip()]
        matched_audience = [term for term in audience_terms if term in text]
        if matched_audience:
            score += min(len(matched_audience) * 5, 15)
            reasons.append("Audience overlap detected from the brand profile.")

    if any("promotion" in rule.lower() or "self-promo" in rule.lower() for rule in subreddit_rules):
        rule_risk.append("Subreddit appears sensitive to promotional replies.")
        score -= 5
    if any("link" in rule.lower() for rule in subreddit_rules):
        rule_risk.append("Subreddit rules mention external links.")

    if score <= 0:
        reasons.append("Weak signal match; keep for manual review only if strategically important.")

    return OpportunityScore(total=max(min(score, 100), 0), keyword_hits=keyword_hits, reasons=reasons, rule_risk=rule_risk)
