"""FastAPI middleware: rate limiting, request tracing, logging."""
import hashlib
import logging
import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter
_rate_store: defaultdict[str, list[float]] = defaultdict(list)
MAX_STORE_KEYS = 10_000

RATE_LIMITS = {
    "default": (60, 60),        # 60 requests per 60 seconds
    "scan": (5, 60),            # 5 scans per 60 seconds
    "generate": (10, 60),       # 10 generations per 60 seconds
    "auth": (10, 300),          # 10 auth attempts per 5 minutes
}

SLOW_ENDPOINTS = {
    "/v1/scans": "scan",
    "/v1/drafts/replies": "generate",
    "/v1/drafts/posts": "generate",
    "/v1/brand/": "generate",
    "/v1/personas/generate": "generate",
    "/v1/discovery/keywords/generate": "generate",
    "/v1/discovery/subreddits/discover": "generate",
    "/v1/auth/login": "auth",
    "/v1/auth/register": "auth",
    "/v1/auth/forgot-password": "auth",
    "/v1/auth/reset-password": "auth",
}


def reset_rate_limit_store() -> None:
    """Clear in-memory rate limit state, primarily for isolated test runs."""
    _rate_store.clear()


def _rate_limit_key(request: Request) -> str:
    """Derive a privacy-preserving rate limit key from auth header or IP."""
    auth_header = request.headers.get("authorization", "")
    if auth_header:
        # Hash the token instead of using raw suffix — prevents token leakage
        return hashlib.sha256(auth_header.encode("utf-8")).hexdigest()[:16]
    return request.client.host if request.client else "unknown"


def _resolve_limit_type(path: str, method: str) -> str:
    """Match path with prefix support for rate limit categories."""
    for prefix, limit_type in SLOW_ENDPOINTS.items():
        if path.startswith(prefix):
            # Stricter scan/generate limits only apply to mutating requests
            if limit_type in ("scan", "generate") and method != "POST":
                return "default"
            return limit_type
    return "default"


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

        key = _rate_limit_key(request)
        path = request.url.path
        limit_type = _resolve_limit_type(path, request.method)
        max_requests, window = RATE_LIMITS[limit_type]

        now = time.time()
        store_key = f"{key}:{limit_type}"

        # Prune expired entries for this key
        _rate_store[store_key] = [t for t in _rate_store[store_key] if t > now - window]

        # Periodically clean up the store to prevent unbounded memory growth
        if len(_rate_store) > MAX_STORE_KEYS:
            expired_keys = [
                k for k, v in _rate_store.items()
                if not v or max(v) < now - 300  # no activity in 5 min
            ]
            for k in expired_keys:
                del _rate_store[k]

        if len(_rate_store[store_key]) >= max_requests:
            logger.warning(f"Rate limit hit: {store_key} ({limit_type})")
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many requests. Limit: {max_requests} per {window}s. Please wait."},
                headers={"Retry-After": str(window)},
            )

        _rate_store[store_key].append(now)
        return await call_next(request)
