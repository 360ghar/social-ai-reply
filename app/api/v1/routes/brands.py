"""Brand profile management endpoints."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from supabase import Client

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_current_user,
    get_current_workspace,
    get_project,
)
from app.db.supabase_client import get_supabase
from app.db.tables.projects import (
    create_brand_profile,
    get_brand_profile_by_project,
)
from app.db.tables.projects import (
    update_brand_profile as update_brand_profile_table,
)
from app.schemas.v1.product import (
    BrandAnalysisRequest,
    BrandProfileRequest,
    BrandProfileResponse,
)
from app.services.product.copilot import ProductCopilot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["brands"])


@router.get("/brand/{project_id}", response_model=BrandProfileResponse)
def get_brand_profile(
    project_id: int,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> BrandProfileResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_project(supabase, workspace["id"], project_id)

    brand = get_brand_profile_by_project(supabase, project_id)
    if not brand:
        brand = create_brand_profile(
            supabase,
            {
                "project_id": project_id,
                "brand_name": project["name"],
                "website_url": None,
                "summary": None,
                "voice_notes": None,
                "product_summary": None,
                "target_audience": None,
                "call_to_action": None,
                "business_domain": None,
                "reddit_username": None,
                "linkedin_url": None,
            },
        )

    return BrandProfileResponse.model_validate(brand)


@router.put("/brand/{project_id}", response_model=BrandProfileResponse)
def update_brand_profile(
    project_id: int,
    payload: BrandProfileRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> BrandProfileResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_project(supabase, workspace["id"], project_id)

    brand = get_brand_profile_by_project(supabase, project_id)
    if not brand:
        brand = create_brand_profile(
            supabase,
            {
                "project_id": project_id,
                "brand_name": project["name"],
            },
        )

    update_data = {
        "brand_name": payload.brand_name.strip(),
        "website_url": str(payload.website_url) if payload.website_url else None,
        "summary": payload.summary,
        "voice_notes": payload.voice_notes,
        "product_summary": payload.product_summary,
        "target_audience": payload.target_audience,
        "call_to_action": payload.call_to_action,
        "reddit_username": payload.reddit_username,
        "linkedin_url": str(payload.linkedin_url) if payload.linkedin_url else None,
    }

    updated = update_brand_profile_table(supabase, brand["id"], update_data)
    return BrandProfileResponse.model_validate(updated)


@router.post("/brand/{project_id}/analyze", response_model=BrandProfileResponse)
def analyze_brand_website(
    project_id: int,
    payload: BrandAnalysisRequest,
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: Client = Depends(get_supabase),
) -> BrandProfileResponse:
    ensure_workspace_membership(supabase, workspace["id"], current_user["id"])
    project = get_project(supabase, workspace["id"], project_id)

    analysis = ProductCopilot().analyze_website(str(payload.website_url))

    brand = get_brand_profile_by_project(supabase, project_id)
    if not brand:
        brand = create_brand_profile(
            supabase,
            {
                "project_id": project_id,
                "brand_name": project["name"],
            },
        )

    update_data = {
        "brand_name": analysis.brand_name,
        "website_url": str(payload.website_url),
        "summary": analysis.summary,
        "product_summary": analysis.product_summary,
        "target_audience": analysis.target_audience,
        "call_to_action": analysis.call_to_action,
        "voice_notes": analysis.voice_notes,
        "last_analyzed_at": datetime.now(UTC).isoformat(),
    }

    updated = update_brand_profile_table(supabase, brand["id"], update_data)
    return BrandProfileResponse.model_validate(updated)
