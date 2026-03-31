"""RedditFlow API — AI Visibility & Community Engagement Platform."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException
from app.db.base import Base
from app.db.session import engine
from app.core.config import get_settings
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
    description="AI Visibility & Community Engagement Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in (settings.cors_origins_raw or "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Custom middleware
from app.middleware import RequestTracingMiddleware, RateLimitMiddleware
app.add_middleware(RequestTracingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Routes
from app.api.v1.routes import router as v1_router
app.include_router(v1_router)


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
def health_check():
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
    return {"status": "healthy" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}


@app.get("/")
def root():
    return {"name": "RedditFlow API", "version": "2.0.0", "status": "running"}
