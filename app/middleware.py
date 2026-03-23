"""FastAPI middleware: rate limiting, request tracing, logging."""
import time
import uuid
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter (use Redis in production)
_rate_store: dict = defaultdict(list)

RATE_LIMITS = {
    "default": (60, 60),        # 60 requests per 60 seconds
    "scan": (5, 60),            # 5 scans per 60 seconds
    "generate": (10, 60),       # 10 generations per 60 seconds
    "auth": (10, 300),          # 10 auth attempts per 5 minutes
}

SLOW_ENDPOINTS = {
    "/api/v1/scans": "scan",
    "/api/v1/drafts/replies": "generate",
    "/api/v1/drafts/posts": "generate",
    "/api/v1/brand/analyze": "generate",
    "/api/v1/personas/generate": "generate",
    "/api/v1/discovery/keywords/generate": "generate",
    "/api/v1/discovery/subreddits/discover": "generate",
    "/api/v1/auth/login": "auth",
    "/api/v1/auth/register": "auth",
}


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)",
            extra={"request_id": request_id},
        )
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        auth_header = request.headers.get("authorization", "")
        key = auth_header[-16:] if auth_header else client_ip

        path = request.url.path
        limit_type = SLOW_ENDPOINTS.get(path, "default")
        max_requests, window = RATE_LIMITS[limit_type]

        now = time.time()
        store_key = f"{key}:{limit_type}"
        _rate_store[store_key] = [t for t in _rate_store[store_key] if t > now - window]

        if len(_rate_store[store_key]) >= max_requests:
            logger.warning(f"Rate limit hit: {store_key} ({limit_type})")
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many requests. Limit: {max_requests} per {window}s. Please wait."},
                headers={"Retry-After": str(window)},
            )

        _rate_store[store_key].append(now)
        return await call_next(request)
