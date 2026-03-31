"""AI Visibility (prompt sets, runs, summaries) endpoints."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.models import AccountUser, BrandProfile, Project, Workspace
from app.db.session import get_db
from app.utils.audit import record_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["visibility"])


@router.get("/prompt-sets")
def list_prompt_sets(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import PromptSet

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")
    sets = db.query(PromptSet).filter(PromptSet.project_id == proj.id).order_by(PromptSet.created_at.desc()).all()
    return {
        "items": [
            {"id": s.id, "name": s.name, "category": s.category,
             "prompts": s.prompts or [], "target_models": s.target_models or [],
             "is_active": s.is_active, "schedule": s.schedule,
             "created_at": s.created_at.isoformat() if s.created_at else None}
            for s in sets
        ]
    }


@router.post("/prompt-sets", status_code=201)
def create_prompt_set(
    payload: dict,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import PromptSet

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")
    ps = PromptSet(
        project_id=proj.id,
        name=payload.get("name", "Untitled"),
        category=payload.get("category", "general"),
        prompts=payload.get("prompts", []),
        target_models=payload.get("target_models", ["chatgpt", "perplexity", "gemini", "claude"]),
        schedule=payload.get("schedule", "manual"),
    )
    db.add(ps)
    db.commit()
    db.refresh(ps)
    record_audit(
        db, workspace_id=workspace.id, project_id=proj.id, actor_user_id=current_user.id,
        event_type="prompt_set.created", entity_type="PromptSet", entity_id=str(ps.id),
    )
    return {"id": ps.id, "name": ps.name}


@router.post("/prompt-sets/{psid}/run")
def run_prompt_set(
    psid: int,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import PromptSet, PromptRun, AIResponse, BrandMention, Citation
    from app.services.product.visibility import ModelRunner, MentionDetector, CitationExtractor

    ensure_workspace_membership(db, workspace.id, current_user.id)
    ps = db.scalar(
        select(PromptSet).join(Project).where(PromptSet.id == psid, Project.workspace_id == workspace.id)
    )
    if not ps:
        raise HTTPException(404, "Prompt set not found.")
    proj = get_project(db, workspace.id, ps.project_id)
    if project_id is not None and proj.id != project_id:
        raise HTTPException(404, "Prompt set not found in the selected project.")

    brand = db.scalar(select(BrandProfile).where(BrandProfile.project_id == proj.id))
    brand_name = brand.brand_name if brand else proj.name
    competitors = []

    runner = ModelRunner()
    detector = MentionDetector()
    extractor = CitationExtractor()

    results = []
    for prompt_text in (ps.prompts or []):
        for model in (ps.target_models or ["chatgpt"]):
            pr = PromptRun(prompt_set_id=ps.id, model_name=model, prompt_text=prompt_text, status="running")
            db.add(pr)
            db.flush()

            response_text = runner.run_prompt(prompt_text, model)
            if response_text:
                pr.status = "complete"
                pr.completed_at = datetime.now(timezone.utc)

                mentions = detector.detect_mentions(response_text, brand_name, competitors)
                citations = extractor.extract_citations(response_text)

                ai_resp = AIResponse(
                    prompt_run_id=pr.id, model_name=model, raw_response=response_text,
                    brand_mentioned=mentions["brand_mentioned"],
                    competitor_mentions=mentions["competitor_mentions"],
                    sentiment=mentions["sentiment"],
                    response_length=len(response_text),
                )
                db.add(ai_resp)
                db.flush()

                if mentions["brand_mentioned"]:
                    db.add(BrandMention(
                        ai_response_id=ai_resp.id, entity_name=brand_name,
                        mention_type="brand", context_snippet=response_text[:200],
                    ))
                for comp in mentions["competitor_mentions"]:
                    db.add(BrandMention(
                        ai_response_id=ai_resp.id, entity_name=comp["name"],
                        mention_type="competitor",
                    ))
                for cit in citations:
                    db.add(Citation(
                        ai_response_id=ai_resp.id, url=cit["url"],
                        domain=cit["domain"], content_type=cit["content_type"],
                    ))

                results.append({"prompt": prompt_text[:80], "model": model, "brand_mentioned": mentions["brand_mentioned"], "citations": len(citations)})
            else:
                pr.status = "failed"
                pr.error_message = "No response from model"
                results.append({"prompt": prompt_text[:80], "model": model, "brand_mentioned": False, "citations": 0, "error": True})

    db.commit()
    record_audit(
        db, workspace_id=workspace.id, project_id=proj.id, actor_user_id=current_user.id,
        event_type="visibility.run", entity_type="PromptSet", entity_id=str(ps.id),
    )
    return {"prompt_set_id": ps.id, "results": results, "total_runs": len(results)}


@router.get("/visibility/summary")
def visibility_summary(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import PromptRun, AIResponse, Citation, PromptSet

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    total_runs = db.query(PromptRun).join(PromptSet).filter(PromptSet.project_id == proj.id, PromptRun.status == "complete").count()
    total_mentioned = db.query(AIResponse).join(PromptRun).join(PromptSet).filter(
        PromptSet.project_id == proj.id, AIResponse.brand_mentioned == True
    ).count()
    total_citations = db.query(Citation).join(AIResponse).join(PromptRun).join(PromptSet).filter(
        PromptSet.project_id == proj.id
    ).count()
    sov = round((total_mentioned / total_runs * 100), 1) if total_runs > 0 else 0.0

    models = {}
    for model in ["chatgpt", "perplexity", "gemini", "claude"]:
        m_total = db.query(PromptRun).join(PromptSet).filter(
            PromptSet.project_id == proj.id, PromptRun.model_name == model, PromptRun.status == "complete"
        ).count()
        m_mentioned = db.query(AIResponse).join(PromptRun).join(PromptSet).filter(
            PromptSet.project_id == proj.id, PromptRun.model_name == model, AIResponse.brand_mentioned == True
        ).count()
        models[model] = {
            "total_runs": m_total,
            "brand_mentioned": m_mentioned,
            "share_of_voice": round((m_mentioned / m_total * 100), 1) if m_total > 0 else 0.0,
        }

    return {
        "total_runs": total_runs,
        "brand_mentioned": total_mentioned,
        "share_of_voice": sov,
        "total_citations": total_citations,
        "models": models,
    }


@router.get("/visibility/prompts")
def visibility_prompt_results(
    limit: int = 20, offset: int = 0, model: str = None,
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    from app.db.models import PromptRun, AIResponse, PromptSet

    ensure_workspace_membership(db, workspace.id, current_user.id)
    proj = get_active_project(db, workspace.id, project_id)
    if not proj:
        raise HTTPException(404, "No active project found.")

    q = db.query(PromptRun).join(PromptSet).filter(PromptSet.project_id == proj.id)
    if model:
        q = q.filter(PromptRun.model_name == model)
    total = q.count()
    runs = q.order_by(PromptRun.scheduled_at.desc()).offset(offset).limit(limit).all()

    items = []
    for r in runs:
        resp = db.query(AIResponse).filter(AIResponse.prompt_run_id == r.id).first()
        items.append({
            "id": r.id, "prompt_text": r.prompt_text, "model_name": r.model_name,
            "status": r.status, "brand_mentioned": resp.brand_mentioned if resp else False,
            "competitor_mentions": resp.competitor_mentions if resp else [],
            "sentiment": resp.sentiment if resp else None,
            "citations_count": len(resp.citations) if resp else 0,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        })
    return {"items": items, "total": total}
