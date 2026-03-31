from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    BrandProfile,
    DiscoveryKeyword,
    MonitoredSubreddit,
    Opportunity,
    OpportunityStatus,
    Project,
    ScanRun,
    ScanStatus,
    SubredditAnalysis,
)
from app.schemas.v1.discovery import ScanRequest
from app.services.product.reddit import RedditClient
from app.services.product.scoring import score_post


def run_scan(db: Session, project: Project, payload: ScanRequest) -> ScanRun:
    reddit = RedditClient()
    brand = project.brand_profile
    active_keywords = db.scalars(
        select(DiscoveryKeyword).where(DiscoveryKeyword.project_id == project.id, DiscoveryKeyword.is_active.is_(True))
    ).all()
    active_subreddits = db.scalars(
        select(MonitoredSubreddit)
        .where(MonitoredSubreddit.project_id == project.id, MonitoredSubreddit.is_active.is_(True))
        .options(selectinload(MonitoredSubreddit.analyses))
    ).all()
    if not active_keywords:
        raise HTTPException(status_code=400, detail="Add discovery keywords before scanning.")
    if not active_subreddits:
        raise HTTPException(status_code=400, detail="Add monitored subreddits before scanning.")

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
        keywords = [row.keyword for row in active_keywords]
        cutoff = datetime.now(timezone.utc) - timedelta(hours=payload.search_window_hours)
        for subreddit in active_subreddits:
            rules = reddit.subreddit_rules(subreddit.name)
            try:
                posts = reddit.search_posts(subreddit.name, keywords, limit=payload.max_posts_per_subreddit)
            except Exception:
                continue
            for post in posts:
                if post.created_at < cutoff:
                    continue
                posts_scanned += 1
                score = score_post(post, brand, subreddit, keywords, rules)
                if score.total < payload.min_score:
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
