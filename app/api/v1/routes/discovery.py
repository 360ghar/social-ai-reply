"""Keyword and subreddit discovery endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.deps import (
    build_subreddit_analysis,
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.models import (
    AccountUser,
    DiscoveryKeyword,
    MonitoredSubreddit,
    Persona,
    Project,
    SubredditAnalysis,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.product import (
    KeywordGenerateRequest,
    KeywordRequest,
    KeywordResponse,
    SubredditDiscoverRequest,
    SubredditRequest,
    SubredditResponse,
)
from app.services.product.copilot import ProductCopilot
from app.services.product.entitlements import (
    count_active_keywords,
    count_active_subreddits,
    enforce_limit,
    get_limit,
)
from app.services.product.reddit import RedditClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["discovery"])


@router.get("/discovery/keywords", response_model=list[KeywordResponse])
def list_keywords(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[KeywordResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    rows = db.scalars(
        select(DiscoveryKeyword).where(DiscoveryKeyword.project_id == project.id).order_by(DiscoveryKeyword.priority_score.desc())
    ).all()
    return [KeywordResponse.model_validate(row) for row in rows]


@router.post("/discovery/keywords", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
def create_keyword(
    payload: KeywordRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> KeywordResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    if payload.is_active:
        enforce_limit(db, workspace, "keywords", count_active_keywords(db, project.id))
    row = DiscoveryKeyword(project_id=project.id, source="manual", **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return KeywordResponse.model_validate(row)


@router.post("/discovery/keywords/generate", response_model=list[KeywordResponse])
def generate_keywords(
    payload: KeywordGenerateRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[KeywordResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    personas = db.scalars(select(Persona).where(Persona.project_id == project.id, Persona.is_active.is_(True))).all()
    generated = ProductCopilot().generate_keywords(project.brand_profile, personas, payload.count)
    created: list[DiscoveryKeyword] = []
    for item in generated:
        existing = db.scalar(
            select(DiscoveryKeyword).where(
                DiscoveryKeyword.project_id == project.id,
                DiscoveryKeyword.keyword == item.keyword,
            )
        )
        if existing:
            continue
        if count_active_keywords(db, project.id) >= get_limit(db, workspace, "keywords"):
            break
        row = DiscoveryKeyword(
            project_id=project.id,
            keyword=item.keyword,
            rationale=item.rationale,
            priority_score=item.priority_score,
            source="generated",
            is_active=True,
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [KeywordResponse.model_validate(row) for row in created]


@router.delete("/discovery/keywords/{keyword_id}")
def delete_keyword(
    keyword_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(DiscoveryKeyword).join(Project).where(DiscoveryKeyword.id == keyword_id, Project.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Keyword not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/discovery/subreddits", response_model=list[SubredditResponse])
def list_subreddits(
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[SubredditResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    rows = db.scalars(
        select(MonitoredSubreddit)
        .where(MonitoredSubreddit.project_id == project.id)
        .options(selectinload(MonitoredSubreddit.analyses))
        .order_by(MonitoredSubreddit.fit_score.desc(), MonitoredSubreddit.subscribers.desc())
    ).all()
    return [SubredditResponse.model_validate(row) for row in rows]


@router.post("/discovery/subreddits", response_model=SubredditResponse, status_code=status.HTTP_201_CREATED)
def create_subreddit(
    payload: SubredditRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SubredditResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    if payload.is_active:
        enforce_limit(db, workspace, "subreddits", count_active_subreddits(db, project.id))
    row = MonitoredSubreddit(project_id=project.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return SubredditResponse.model_validate(row)


@router.post("/discovery/subreddits/discover", response_model=list[SubredditResponse])
def discover_subreddits(
    payload: SubredditDiscoverRequest,
    project_id: int = Query(..., ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[SubredditResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    keywords = db.scalars(
        select(DiscoveryKeyword)
        .where(DiscoveryKeyword.project_id == project.id, DiscoveryKeyword.is_active.is_(True))
        .order_by(DiscoveryKeyword.priority_score.desc())
    ).all()
    if not keywords:
        raise HTTPException(status_code=400, detail="Generate or add keywords before discovering subreddits.")
    reddit = RedditClient()
    created: list[MonitoredSubreddit] = []
    seen_names = {
        row.name.lower()
        for row in db.scalars(select(MonitoredSubreddit).where(MonitoredSubreddit.project_id == project.id)).all()
    }
    for keyword in keywords[:5]:
        try:
            matches = reddit.search_subreddits(keyword.keyword, limit=payload.max_subreddits)
        except Exception:
            continue
        for match in matches:
            if count_active_subreddits(db, project.id) >= get_limit(db, workspace, "subreddits"):
                break
            if match.name.lower() in seen_names:
                continue
            rules = reddit.subreddit_rules(match.name)
            fit_score = min(100, 35 + keyword.priority_score // 2)
            activity_score = min(100, 20 + int(match.subscribers > 10000) * 20 + int(match.subscribers > 100000) * 20)
            row = MonitoredSubreddit(
                project_id=project.id,
                name=match.name,
                title=match.title,
                description=match.description,
                subscribers=match.subscribers,
                activity_score=activity_score,
                fit_score=fit_score,
                rules_summary="\n".join(rules[:5]) if rules else None,
                is_active=True,
            )
            db.add(row)
            db.flush()
            top_post_types, audience_signals, posting_risk, recommendation = build_subreddit_analysis(
                match.name, match.description, rules,
            )
            db.add(
                SubredditAnalysis(
                    monitored_subreddit_id=row.id,
                    top_post_types=top_post_types,
                    audience_signals=audience_signals,
                    posting_risk=posting_risk,
                    recommendation=recommendation,
                )
            )
            seen_names.add(match.name.lower())
            created.append(row)
        if len(created) >= payload.max_subreddits:
            break
    db.commit()
    for row in created:
        db.refresh(row)
    return [SubredditResponse.model_validate(row) for row in created]


@router.post("/subreddits/{subreddit_id}/analyze", response_model=SubredditResponse)
def analyze_subreddit(
    subreddit_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SubredditResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    subreddit = db.scalar(
        select(MonitoredSubreddit)
        .join(Project)
        .where(MonitoredSubreddit.id == subreddit_id, Project.workspace_id == workspace.id)
        .options(selectinload(MonitoredSubreddit.analyses))
    )
    if not subreddit:
        raise HTTPException(status_code=404, detail="Subreddit not found.")
    reddit = RedditClient()
    about = reddit.subreddit_about(subreddit.name)
    rules = reddit.subreddit_rules(subreddit.name)
    subreddit.title = about.get("title") or subreddit.title
    subreddit.description = about.get("public_description") or subreddit.description
    subreddit.subscribers = int(about.get("subscribers") or subreddit.subscribers or 0)
    top_post_types, audience_signals, posting_risk, recommendation = build_subreddit_analysis(
        subreddit.name, subreddit.description or "", rules,
    )
    db.add(
        SubredditAnalysis(
            monitored_subreddit_id=subreddit.id,
            top_post_types=top_post_types,
            audience_signals=audience_signals,
            posting_risk=posting_risk,
            recommendation=recommendation,
        )
    )
    db.commit()
    db.refresh(subreddit)
    return SubredditResponse.model_validate(subreddit)


@router.delete("/discovery/subreddits/{subreddit_id}")
def delete_subreddit(
    subreddit_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    row = db.scalar(
        select(MonitoredSubreddit).join(Project).where(MonitoredSubreddit.id == subreddit_id, Project.workspace_id == workspace.id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Subreddit not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}
