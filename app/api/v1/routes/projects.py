import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import (
    ensure_workspace_membership,
    get_active_project,
    get_current_user,
    get_current_workspace,
    get_project,
    subscription_response,
)
from app.db.models import (
    AccountUser,
    BrandProfile,
    MonitoredSubreddit,
    Opportunity,
    Persona,
    Project,
    ProjectStatus,
    Workspace,
)
from app.db.session import get_db
from app.schemas.v1.product import (
    DashboardResponse,
    OpportunityResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    SetupStatus,
)
from app.services.product.entitlements import count_projects, enforce_limit
from app.utils.audit import record_audit as _record_audit
from app.utils.slug import unique_slug as _unique_slug

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["projects"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    project_id: int | None = Query(default=None, ge=1),
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    projects = db.scalars(select(Project).where(Project.workspace_id == workspace.id).order_by(Project.created_at.desc())).all()
    selected_project = get_active_project(db, workspace.id, project_id)
    project_ids = [selected_project.id] if selected_project else [project.id for project in projects]
    top_opportunities = []
    if project_ids:
        top_opportunities = db.scalars(
            select(Opportunity)
            .where(Opportunity.project_id.in_(project_ids))
            .order_by(Opportunity.score.desc(), Opportunity.created_at.desc())
            .limit(12)
        ).all()
    # Build setup status from first active project
    setup = SetupStatus()
    if selected_project:
        pid = selected_project.id
        brand = db.scalar(select(BrandProfile).where(BrandProfile.project_id == pid))
        setup.brand_configured = brand is not None and bool(brand.brand_name)
        setup.personas_count = db.scalar(select(func.count()).select_from(Persona).where(Persona.project_id == pid)) or 0
        setup.subreddits_count = db.scalar(select(func.count()).select_from(MonitoredSubreddit).where(MonitoredSubreddit.project_id == pid)) or 0
    elif project_ids:
        pid = project_ids[0]
        brand = db.scalar(select(BrandProfile).where(BrandProfile.project_id == pid))
        setup.brand_configured = brand is not None and bool(brand.brand_name)
        setup.personas_count = db.scalar(select(func.count()).select_from(Persona).where(Persona.project_id == pid)) or 0
        setup.subreddits_count = db.scalar(select(func.count()).select_from(MonitoredSubreddit).where(MonitoredSubreddit.project_id == pid)) or 0

    return DashboardResponse(
        projects=[ProjectResponse.model_validate(project) for project in projects],
        top_opportunities=[OpportunityResponse.model_validate(item) for item in top_opportunities],
        subscription=subscription_response(db, workspace),
        setup_status=setup,
    )


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> list[ProjectResponse]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    rows = db.scalars(select(Project).where(Project.workspace_id == workspace.id).order_by(Project.created_at.desc())).all()
    return [ProjectResponse.model_validate(row) for row in rows]


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    from app.db.models import BrandProfile
    from app.api.v1.deps import ensure_default_prompts
    enforce_limit(db, workspace, "projects", count_projects(db, workspace.id))
    project = Project(
        workspace_id=workspace.id,
        name=payload.name.strip(),
        slug=_unique_slug(db, Project, payload.name, "workspace_id", workspace.id),
        description=payload.description,
        status=ProjectStatus.ACTIVE,
    )
    db.add(project)
    db.flush()
    db.add(BrandProfile(project_id=project.id, brand_name=project.name))
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project.id,
        actor_user_id=current_user.id,
        event_type="project.created",
        entity_type="project",
        entity_id=str(project.id),
        payload={"name": project.name},
    )
    db.commit()
    ensure_default_prompts(db, project.id)
    db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    project.name = payload.name.strip()
    project.description = payload.description
    project.status = ProjectStatus(payload.status)
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project.id,
        actor_user_id=current_user.id,
        event_type="project.updated",
        entity_type="project",
        entity_id=str(project.id),
    )
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    current_user: AccountUser = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    ensure_workspace_membership(db, workspace.id, current_user.id)
    project = get_project(db, workspace.id, project_id)
    db.delete(project)
    _record_audit(
        db,
        workspace_id=workspace.id,
        project_id=project_id,
        actor_user_id=current_user.id,
        event_type="project.deleted",
        entity_type="project",
        entity_id=str(project_id),
    )
    db.commit()
    return {"ok": True}
