"""Citation, source domain, and source gap endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.api.v1.deps import ensure_workspace_membership, get_active_project, get_current_user, get_current_workspace
from app.db.models import AccountUser, Workspace
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["citations"])


@router.get("/citations")
def list_citations(
    limit: int = 20, offset: int = 0, domain: str = None,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import Citation, AIResponse, PromptRun, PromptSet

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    q = db.query(Citation).join(AIResponse).join(PromptRun).join(PromptSet).filter(PromptSet.project_id == proj.id)
    if domain:
        q = q.filter(Citation.domain.contains(domain))
    total = q.count()
    items = q.order_by(Citation.first_seen_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {"id": c.id, "url": c.url, "domain": c.domain, "title": c.title,
             "content_type": c.content_type,
             "first_seen_at": c.first_seen_at.isoformat() if c.first_seen_at else None}
            for c in items
        ],
        "total": total,
    }


@router.get("/sources/domains")
def source_domains(
    limit: int = 20,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import Citation, AIResponse, PromptRun, PromptSet

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    results = db.query(
        Citation.domain,
        sqlfunc.count(Citation.id).label("total"),
    ).join(AIResponse).join(PromptRun).join(PromptSet).filter(
        PromptSet.project_id == proj.id
    ).group_by(Citation.domain).order_by(sqlfunc.count(Citation.id).desc()).limit(limit).all()

    return {"items": [{"domain": r[0], "total_citations": r[1]} for r in results]}


@router.get("/sources/gaps")
def source_gaps(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import SourceGap

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    gaps = db.query(SourceGap).filter(SourceGap.project_id == proj.id).order_by(SourceGap.citation_count.desc()).all()
    return {
        "items": [
            {"id": g.id, "competitor_name": g.competitor_name, "domain": g.domain,
             "citation_count": g.citation_count, "gap_type": g.gap_type,
             "discovered_at": g.discovered_at.isoformat() if g.discovered_at else None}
            for g in gaps
        ]
    }
