"""RedditFlow API - AI Visibility and Community Engagement Platform.

Backend API server using FastAPI with Supabase for authentication and database.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.db.supabase_client import get_supabase_client
from app.middleware import RateLimitMiddleware, RequestTracingMiddleware

setup_logging("INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    In the Supabase era, we don't create tables automatically since
    Supabase manages the schema. Tables should be created via Supabase
    dashboard, migrations, or SQL scripts.
    """
    logger.info("Starting RedditFlow API...")
    # Note: Table creation is now managed via Supabase dashboard/migrations
    # Base.metadata.create_all(bind=engine) is no longer used
    logger.info("RedditFlow API started successfully.")
    yield
    logger.info("Shutting down RedditFlow API.")


settings = get_settings()
app = FastAPI(
    title="RedditFlow API",
    description="AI Visibility and Community Engagement Platform",
    version="2.1.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in (settings.cors_origins_raw or "http://localhost:3000").split(",")]

# Starlette executes middleware in reverse order of addition.
# CORSMiddleware MUST be added last so it runs first — otherwise rate-limit
# or tracing responses won't carry CORS headers and the browser will block them.
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(v1_router)


@app.exception_handler(AppError)
async def app_exception_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _service_checks() -> dict[str, str]:
    """Check service health (API + Supabase database)."""
    checks = {"api": "ok"}
    try:
        supabase = get_supabase_client()
        # Actually query the database to verify connectivity
        supabase.table("account_users").select("id").limit(1).execute()
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Supabase health check failed: %s", e)
        checks["database"] = "error"
    return checks


@app.get("/health")
def health_check():
    """Health check endpoint."""
    checks = _service_checks()
    status = "healthy" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@app.get("/ready")
def readiness_check():
    """Readiness check endpoint."""
    checks = _service_checks()
    ready = all(value == "ok" for value in checks.values())
    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    return JSONResponse(content=payload, status_code=200 if ready else 503)


@app.get("/")
def root():
    """Root endpoint."""
    return {"name": "RedditFlow API", "version": "2.1.0", "status": "running"}
