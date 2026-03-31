"""Route aggregator for /v1 API.

Each domain router lives in its own module under this package.
"""

from fastapi import APIRouter

from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.auto_pipeline import router as auto_pipeline_router
from app.api.v1.routes.billing import router as billing_router
from app.api.v1.routes.brands import router as brands_router
from app.api.v1.routes.campaigns import router as campaigns_router
from app.api.v1.routes.citations import router as citations_router
from app.api.v1.routes.discovery import router as discovery_router
from app.api.v1.routes.drafts import router as drafts_router
from app.api.v1.routes.invitations import router as invitations_router
from app.api.v1.routes.notifications import router as notifications_router
from app.api.v1.routes.opportunities import router as opportunities_router
from app.api.v1.routes.personas import router as personas_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.prompts import router as prompts_router
from app.api.v1.routes.reddit_posting import router as reddit_posting_router
from app.api.v1.routes.scans import router as scans_router
from app.api.v1.routes.secrets import router as secrets_router
from app.api.v1.routes.visibility import router as visibility_router
from app.api.v1.routes.webhooks import router as webhooks_router
from app.api.v1.routes.workspace import router as workspace_router

router = APIRouter()

router.include_router(analytics_router)
router.include_router(auth_router)
router.include_router(auto_pipeline_router)
router.include_router(billing_router)
router.include_router(brands_router)
router.include_router(campaigns_router)
router.include_router(citations_router)
router.include_router(discovery_router)
router.include_router(drafts_router)
router.include_router(invitations_router)
router.include_router(notifications_router)
router.include_router(opportunities_router)
router.include_router(personas_router)
router.include_router(projects_router)
router.include_router(prompts_router)
router.include_router(reddit_posting_router)
router.include_router(scans_router)
router.include_router(secrets_router)
router.include_router(visibility_router)
router.include_router(webhooks_router)
router.include_router(workspace_router)
