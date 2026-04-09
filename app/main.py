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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RedditFlow API...")
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


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def _service_checks() -> dict[str, str]:
    from sqlalchemy import text

    checks = {"api": "ok"}
    try:
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
        finally:
            db.close()
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
    ready = all(value == "ok" for value in checks.values())
    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    return JSONResponse(content=payload, status_code=200 if ready else 503)


@app.get("/")
def root():
    return {"name": "RedditFlow API", "version": "2.0.0", "status": "running"}
