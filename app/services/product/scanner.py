from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    DiscoveryKeyword,
    MonitoredSubreddit,
    Opportunity,
    OpportunityStatus,
    Project,
    ScanRun,
    ScanStatus,
)
from app.schemas.v1.discovery import ScanRequest
from app.services.product.discovery import get_project_search_keywords
from app.services.product.reddit import RedditClient, RedditPost
from app.services.product.scoring import (
    MIN_RELEVANT_OPPORTUNITY_SCORE,
    MIN_SUBREDDIT_FIT_FOR_AUTOMATION,
    score_post,
)


def run_scan(db: Session, project: Project, payload: ScanRequest) -> ScanRun:
    reddit = RedditClient()
    brand = project.brand_profile
    active_keywords = db.scalars(
        select(DiscoveryKeyword)
        .where(DiscoveryKeyword.project_id == project.id, DiscoveryKeyword.is_active.is_(True))
        .order_by(DiscoveryKeyword.priority_score.desc())
    ).all()
    active_subreddits = db.scalars(
        select(MonitoredSubreddit)
        .where(MonitoredSubreddit.project_id == project.id, MonitoredSubreddit.is_active.is_(True))
        .options(selectinload(MonitoredSubreddit.analyses))
        .order_by(MonitoredSubreddit.fit_score.desc(), MonitoredSubreddit.subscribers.desc())
    ).all()
    if not active_keywords:
        raise HTTPException(status_code=400, detail="Add discovery keywords before scanning.")
    if not active_subreddits:
        raise HTTPException(status_code=400, detail="Add monitored subreddits before scanning.")

    search_keywords = get_project_search_keywords(db, project, limit=12)
    if not search_keywords:
        raise HTTPException(status_code=400, detail="Add more specific discovery keywords before scanning.")

    run = ScanRun(
        project_id=project.id,
        status=ScanStatus.RUNNING,
        search_window_hours=payload.search_window_hours,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        posts_scanned = 0
        opportunities_found = 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=payload.search_window_hours)
        effective_min_score = max(payload.min_score, MIN_RELEVANT_OPPORTUNITY_SCORE)
        rules_cache: dict[str, list[str]] = {}

        for subreddit in active_subreddits:
            if subreddit.fit_score < MIN_SUBREDDIT_FIT_FOR_AUTOMATION:
                continue
            rules = rules_cache.setdefault(subreddit.name.lower(), _safe_subreddit_rules(reddit, subreddit.name))
            try:
                posts = reddit.search_posts(subreddit.name, search_keywords, limit=payload.max_posts_per_subreddit)
            except Exception:
                continue
            for post in posts:
                if post.created_at < cutoff:
                    continue
                posts_scanned += 1
                score = score_post(post, brand, subreddit, search_keywords, rules)
                if not score.eligible or score.total < effective_min_score:
                    continue
                opportunity = db.scalar(
                    select(Opportunity).where(
                        Opportunity.project_id == project.id,
                        Opportunity.reddit_post_id == post.post_id,
                    )
                )
                if opportunity:
                    opportunity.score = score.total
                    opportunity.score_reasons = score.reasons
                    opportunity.keyword_hits = score.keyword_hits
                    opportunity.rule_risk = score.rule_risk
                    opportunity.body_excerpt = post.body[:1200]
                    opportunity.permalink = post.permalink
                else:
                    db.add(
                        Opportunity(
                            project_id=project.id,
                            scan_run_id=run.id,
                            reddit_post_id=post.post_id,
                            subreddit_name=post.subreddit,
                            author=post.author,
                            title=post.title,
                            permalink=post.permalink,
                            body_excerpt=post.body[:1200],
                            score=score.total,
                            status=OpportunityStatus.NEW,
                            score_reasons=score.reasons,
                            keyword_hits=score.keyword_hits,
                            rule_risk=score.rule_risk,
                        )
                    )
                    opportunities_found += 1

        _revalidate_open_opportunities(
            db,
            project=project,
            active_subreddits=active_subreddits,
            search_keywords=search_keywords,
            min_score=effective_min_score,
            reddit=reddit,
            rules_cache=rules_cache,
        )

        run.status = ScanStatus.COMPLETED
        run.posts_scanned = posts_scanned
        run.opportunities_found = opportunities_found
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.scalar(select(ScanRun).where(ScanRun.id == run.id))
        if run:
            run.status = ScanStatus.FAILED
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            db.add(run)
            db.commit()
        raise
    return run


def revalidate_opportunity(
    db: Session,
    project: Project,
    opportunity: Opportunity,
    *,
    reddit: RedditClient | None = None,
) -> tuple[bool, int]:
    reddit = reddit or RedditClient()
    search_keywords = get_project_search_keywords(db, project, limit=12)
    if not search_keywords:
        return False, 0

    subreddit = db.scalar(
        select(MonitoredSubreddit).where(
            MonitoredSubreddit.project_id == project.id,
            MonitoredSubreddit.name == opportunity.subreddit_name,
        )
    )
    if not subreddit or subreddit.fit_score < MIN_SUBREDDIT_FIT_FOR_AUTOMATION:
        opportunity.score = 0
        opportunity.score_reasons = ["Rejected: subreddit no longer meets the fit threshold for automated discovery."]
        opportunity.keyword_hits = []
        opportunity.rule_risk = []
        return False, 0

    rules = _safe_subreddit_rules(reddit, subreddit.name)
    snapshot = RedditPost(
        post_id=opportunity.reddit_post_id,
        subreddit=opportunity.subreddit_name,
        title=opportunity.title,
        author=opportunity.author,
        permalink=opportunity.permalink,
        body=opportunity.body_excerpt or "",
        created_at=opportunity.created_at,
        num_comments=25,
        score=opportunity.score,
    )
    assessment = score_post(snapshot, project.brand_profile, subreddit, search_keywords, rules)
    opportunity.score = assessment.total
    opportunity.score_reasons = assessment.reasons
    opportunity.keyword_hits = assessment.keyword_hits
    opportunity.rule_risk = assessment.rule_risk
    return assessment.eligible, assessment.total


def _revalidate_open_opportunities(
    db: Session,
    *,
    project: Project,
    active_subreddits: list[MonitoredSubreddit],
    search_keywords: list[str],
    min_score: int,
    reddit: RedditClient,
    rules_cache: dict[str, list[str]],
) -> None:
    subreddit_map = {row.name.lower(): row for row in active_subreddits}
    open_rows = db.scalars(
        select(Opportunity).where(
            Opportunity.project_id == project.id,
            Opportunity.status.in_([OpportunityStatus.NEW, OpportunityStatus.SAVED]),
        )
    ).all()

    for opportunity in open_rows:
        subreddit = subreddit_map.get(opportunity.subreddit_name.lower())
        if not subreddit or subreddit.fit_score < MIN_SUBREDDIT_FIT_FOR_AUTOMATION:
            opportunity.status = OpportunityStatus.IGNORED
            opportunity.score = 0
            opportunity.score_reasons = ["Rejected: subreddit no longer meets the fit threshold for automated discovery."]
            opportunity.keyword_hits = []
            opportunity.rule_risk = []
            continue

        rules = rules_cache.setdefault(subreddit.name.lower(), _safe_subreddit_rules(reddit, subreddit.name))
        snapshot = RedditPost(
            post_id=opportunity.reddit_post_id,
            subreddit=opportunity.subreddit_name,
            title=opportunity.title,
            author=opportunity.author,
            permalink=opportunity.permalink,
            body=opportunity.body_excerpt or "",
            created_at=opportunity.created_at,
            num_comments=25,
            score=opportunity.score,
        )
        assessment = score_post(snapshot, project.brand_profile, subreddit, search_keywords, rules)
        opportunity.score = assessment.total
        opportunity.score_reasons = assessment.reasons
        opportunity.keyword_hits = assessment.keyword_hits
        opportunity.rule_risk = assessment.rule_risk
        if not assessment.eligible or assessment.total < min_score:
            opportunity.status = OpportunityStatus.IGNORED


def _safe_subreddit_rules(reddit: RedditClient, name: str) -> list[str]:
    try:
        return reddit.subreddit_rules(name)
    except Exception:
        return []
