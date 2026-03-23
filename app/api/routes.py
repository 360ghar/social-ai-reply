from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import CrawlRun
from app.db.session import get_db
from app.exporters.csv_exporter import export_handle_metrics
from app.schemas.analytics import QueryResponse
from app.schemas.persona import BusinessInputRequest, PersonaPlanResponse
from app.schemas.scraping import ScrapeRequest, ScrapeRunResponse
from app.services.analytics_service import AnalyticsService
from app.services.instagram_client import InstagrapiClientAdapter
from app.services.llm import select_llm_provider
from app.services.persona_engine import PersonaEngine
from app.services.proxy_pool import ProxyPool
from app.services.rate_limiter import AccountRateLimiter
from app.services.scraper_engine import ScraperEngine


router = APIRouter()
_client_lock = Lock()
_client_cache: dict[str, InstagrapiClientAdapter] = {}


def _build_instagram_client(challenge_code: str | None = None) -> InstagrapiClientAdapter:
    settings = get_settings()
    if not settings.instagram_username or not settings.instagram_password:
        raise HTTPException(
            status_code=400,
            detail="Instagram credentials missing. Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env.",
        )
    effective_challenge_code = challenge_code or settings.instagram_challenge_code
    cache_key = settings.instagram_username

    with _client_lock:
        existing = _client_cache.get(cache_key)
        if existing:
            existing.set_challenge_code(effective_challenge_code)
            return existing

        limiter = AccountRateLimiter(
            requests_per_minute=settings.scrape_requests_per_minute,
            daily_cap=settings.scrape_daily_cap_per_account,
        )
        proxy_pool = ProxyPool(settings.proxies)
        client = InstagrapiClientAdapter(
            username=settings.instagram_username,
            password=settings.instagram_password,
            session_dir=settings.instagram_session_dir,
            rate_limiter=limiter,
            proxy_pool=proxy_pool,
            challenge_code=effective_challenge_code,
        )
        _client_cache[cache_key] = client
        return client


@router.post("/phase1/persona-plan", response_model=PersonaPlanResponse)
def generate_persona_plan(payload: BusinessInputRequest, db: Session = Depends(get_db)) -> PersonaPlanResponse:
    settings = get_settings()
    provider = select_llm_provider(
        settings.use_mock_llm,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        gemini_api_url=settings.gemini_api_url,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
    )
    service = PersonaEngine(provider)
    return service.build_plan(payload, db=db)


@router.post("/phase2/scrape/run", response_model=ScrapeRunResponse)
def run_scrape(payload: ScrapeRequest, db: Session = Depends(get_db)) -> ScrapeRunResponse:
    if payload.run_async:
        from app.workers.tasks import run_scrape_task

        task = run_scrape_task.delay(payload.model_dump(mode="json"))
        return ScrapeRunResponse(
            run_id=task.id,
            status="queued",
            profiles_discovered=0,
            interactions_collected=0,
            sample_profiles=[],
        )

    client = _build_instagram_client(challenge_code=payload.challenge_code)
    service = ScraperEngine(db=db, instagram_client=client)
    return service.run(payload)


@router.get("/phase2/scrape/runs/{run_id}", response_model=ScrapeRunResponse)
def get_scrape_run(run_id: str, db: Session = Depends(get_db)) -> ScrapeRunResponse:
    run = db.scalar(select(CrawlRun).where(CrawlRun.id == run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return ScrapeRunResponse(
        run_id=run.id,
        status=run.status.value,
        profiles_discovered=run.profiles_discovered,
        interactions_collected=run.interactions_collected,
        started_at=run.started_at,
        finished_at=run.finished_at,
        sample_profiles=[],
    )


@router.get("/phase4/super-fans", response_model=QueryResponse)
def query_super_fans(
    min_profiles: int = Query(default=15, ge=1, le=1000),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> QueryResponse:
    return AnalyticsService(db).super_fans(min_profiles=min_profiles, limit=limit)


@router.get("/phase4/top-commenters", response_model=QueryResponse)
def query_top_commenters(
    min_comments: int = Query(default=3, ge=1, le=5000),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> QueryResponse:
    return AnalyticsService(db).top_commenters(min_comments=min_comments, limit=limit)


@router.get("/phase4/frequent-likers", response_model=QueryResponse)
def query_frequent_likers(
    min_likes: int = Query(default=5, ge=1, le=5000),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> QueryResponse:
    return AnalyticsService(db).frequent_likers(min_likes=min_likes, limit=limit)


@router.get("/phase4/export/{query_name}")
def export_query(
    query_name: str,
    threshold: int = Query(default=5, ge=1, le=5000),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    if query_name == "super_fans":
        response = service.super_fans(min_profiles=threshold, limit=limit)
    elif query_name == "top_commenters":
        response = service.top_commenters(min_comments=threshold, limit=limit)
    elif query_name == "frequent_likers":
        response = service.frequent_likers(min_likes=threshold, limit=limit)
    else:
        raise HTTPException(status_code=400, detail="query_name must be super_fans, top_commenters, or frequent_likers")

    csv_path = export_handle_metrics(response.results, query_name=response.query_name)
    response.csv_path = csv_path
    return FileResponse(csv_path, media_type="text/csv", filename=Path(csv_path).name)
