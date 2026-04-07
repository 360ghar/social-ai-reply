"""RedditFlow API - AI Visibility and Community Engagement Platform."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.db.base import Base
from app.db.session import engine
from app.middleware import RateLimitMiddleware, RequestTracingMiddleware
from app.services.product.logging_config import setup_logging

setup_logging("INFO")
logger = logging.getLogger(__name__)


def _migrate_auth_schema(bind) -> None:
    """Apply lightweight startup migrations for older local/dev databases."""
    from sqlalchemy import inspect, text

    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    timestamp_type = "DATETIME" if bind.dialect.name == "sqlite" else "TIMESTAMP WITH TIME ZONE"

    with bind.begin() as conn:
        if "account_users" in table_names:
            account_user_columns = {col["name"] for col in inspector.get_columns("account_users")}
            if "supabase_user_id" not in account_user_columns:
                conn.execute(text("ALTER TABLE account_users ADD COLUMN supabase_user_id VARCHAR(255)"))
                logger.info("Migration: added supabase_user_id column to account_users.")
            if "password_hash" not in account_user_columns:
                conn.execute(text("ALTER TABLE account_users ADD COLUMN password_hash VARCHAR(255)"))
                logger.info("Migration: added password_hash column to account_users.")
            if "tokens_invalid_before" not in account_user_columns:
                conn.execute(text(f"ALTER TABLE account_users ADD COLUMN tokens_invalid_before {timestamp_type}"))
                logger.info("Migration: added tokens_invalid_before column to account_users.")
            if "revoked_access_token_hash" not in account_user_columns:
                conn.execute(text("ALTER TABLE account_users ADD COLUMN revoked_access_token_hash VARCHAR(64)"))
                logger.info("Migration: added revoked_access_token_hash column to account_users.")

        if "brand_profiles" in table_names:
            brand_profile_columns = {col["name"] for col in inspector.get_columns("brand_profiles")}
            if "business_domain" not in brand_profile_columns:
                conn.execute(text("ALTER TABLE brand_profiles ADD COLUMN business_domain VARCHAR(255)"))
                logger.info("Migration: added business_domain column to brand_profiles.")

        if "password_reset_tokens" in table_names:
            conn.execute(text("DROP TABLE IF EXISTS password_reset_tokens"))
            logger.info("Migration: dropped password_reset_tokens table.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RedditFlow API...")
    _migrate_auth_schema(engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
    yield
    logger.info("Shutting down RedditFlow API.")


settings = get_settings()
app = FastAPI(
    title="RedditFlow API",
    description="AI Visibility and Community Engagement Platform",
    version="2.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in (settings.cors_origins_raw or "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.include_router(v1_router)


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _service_checks() -> dict[str, str]:
    from sqlalchemy import text

    checks = {"api": "ok"}
    try:
        from app.db.session import SessionLocal

        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    return checks


@app.get("/health")
def health_check():
    checks = _service_checks()
    status = "healthy" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@app.get("/ready")
def readiness_check():
    checks = _service_checks()
    status = "ready" if all(value == "ok" for value in checks.values()) else "not_ready"
    return {"status": status, "checks": checks}


@app.get("/")
def root():
    return {"name": "RedditFlow API", "version": "2.0.0", "status": "running"}
