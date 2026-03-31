import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.models import (
    AccountUser,
    BrandProfile,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.product import (
    BrandAnalysisRequest,
    BrandProfileRequest,
    BrandProfileResponse,
)
from app.services.product.copilot import ProductCopilot
from app.utils.audit import record_audit as _record_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["brands"])


@router.get("/brand/{project_id}", response_model=BrandProfileResponse)
def get_brand_profile(
    project_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> BrandProfileResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    if not project.brand_profile:
        brand = BrandProfile(project_id=project.id, brand_name=project.name)
        db.add(brand)
        db.commit()
        db.refresh(brand)
        return BrandProfileResponse.model_validate(brand)
    return BrandProfileResponse.model_validate(project.brand_profile)


@router.put("/brand/{project_id}", response_model=BrandProfileResponse)
def update_brand_profile(
    project_id: int,
    payload: BrandProfileRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> BrandProfileResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    brand = project.brand_profile or BrandProfile(project_id=project.id, brand_name=project.name)
    if brand.id is None:
        db.add(brand)
    brand.brand_name = payload.brand_name.strip()
    brand.website_url = str(payload.website_url) if payload.website_url else None
    brand.summary = payload.summary
    brand.voice_notes = payload.voice_notes
    brand.product_summary = payload.product_summary
    brand.target_audience = payload.target_audience
    brand.call_to_action = payload.call_to_action
    brand.reddit_username = payload.reddit_username
    brand.linkedin_url = str(payload.linkedin_url) if payload.linkedin_url else None
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project.id,
        actor_user_id=current_user.id,
        event_type="brand.updated",
        entity_type="brand_profile",
        entity_id=str(project.id),
    )
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)


@router.post("/brand/{project_id}/analyze", response_model=BrandProfileResponse)
def analyze_brand_website(
    project_id: int,
    payload: BrandAnalysisRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> BrandProfileResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    analysis = ProductCopilot().analyze_website(str(payload.website_url))
    brand = project.brand_profile or BrandProfile(project_id=project.id, brand_name=project.name)
    if brand.id is None:
        db.add(brand)
    brand.brand_name = analysis.brand_name
    brand.website_url = str(payload.website_url)
    brand.summary = analysis.summary
    brand.product_summary = analysis.product_summary
    brand.target_audience = analysis.target_audience
    brand.call_to_action = analysis.call_to_action
    brand.voice_notes = analysis.voice_notes
    brand.last_analyzed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(brand)
    return BrandProfileResponse.model_validate(brand)
