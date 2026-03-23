from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas.scraping import ScrapeRequest
from app.services.instagram_client import InstagrapiClientAdapter
from app.services.proxy_pool import ProxyPool
from app.services.rate_limiter import AccountRateLimiter
from app.services.scraper_engine import ScraperEngine
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.run_scrape_task")
def run_scrape_task(payload: dict) -> dict:
    settings = get_settings()
    if not settings.instagram_username or not settings.instagram_password:
        return {
            "status": "failed",
            "error": "Instagram credentials missing in environment.",
            "profiles_discovered": 0,
            "interactions_collected": 0,
        }

    request = ScrapeRequest.model_validate(payload)
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
        challenge_code=request.challenge_code or settings.instagram_challenge_code,
    )

    db = SessionLocal()
    try:
        result = ScraperEngine(db=db, instagram_client=client).run(request)
        return result.model_dump(mode="json")
    finally:
        db.close()
