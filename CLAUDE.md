# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RedditFlow is a hosted SaaS platform for finding relevant Reddit posts, scoring opportunities, and drafting helpful replies. It does **not** auto-post to Reddit — all posting is manual. The product layers are:

- **Backend** (`app/`): FastAPI API server with Supabase Auth (JWT), workspace-scoped multi-tenancy, LLM-powered analysis/drafting, Reddit scraping, billing/entitlements, and Supabase Postgres database.
- **Frontend** (`web/`): Next.js 16 app with React 19, shadcn/ui components (built on `@base-ui/react`), Tailwind CSS v4, and Zustand state management. `AuthProvider` context wraps all routes.

## Commands

### Backend
```bash
# Setup
cp .env.example .env
uv sync --extra dev

# Run dev server
uv run uvicorn app.main:app --reload

# Run all tests
uv run pytest -q

# Run a single test file
uv run pytest tests/unit/test_security.py -q

# Lint
uv run ruff check app/ tests/

# Auto-fix lint
uv run ruff check --fix app/ tests/
```

### Frontend
```bash
cd web
npm install
npm run dev       # dev server at localhost:3000
npm run build     # type-check + production build (used as the "test" step)
```

## Backend Architecture

**Entry point**: `app/main.py` — creates the FastAPI app, registers CORS, custom middleware (request tracing + rate limiting), mounts all v1 routes.

**API surface**: All routes live under `/v1` in the URL. Route files are in `app/api/v1/routes/`, each domain in its own module (auth, projects, discovery, drafts, scans, billing, etc.). Routes are aggregated in `app/api/v1/routes/__init__.py`.

**Dependencies** (`app/api/v1/deps.py`): Central file providing `get_current_user`, `get_current_workspace`, `get_project`, `get_active_project`, `ensure_default_prompts`, and helper functions. All authenticated endpoints depend on these.

**Database Layer** (`app/db/`):
- `supabase_client.py` — Singleton Supabase client with `get_supabase()` FastAPI dependency
- `tables/` — Typed helper functions for all table operations organized by domain:
  - `users.py` — AccountUser operations
  - `workspaces.py` — Workspace, Membership, Invitation, Subscription, PlanEntitlement, Redemption operations
  - `projects.py` — Project, BrandProfile, PromptTemplate operations
  - `discovery.py` — Persona, DiscoveryKeyword, MonitoredSubreddit, Opportunity, ScanRun operations
  - `content.py` — ReplyDraft, PostDraft operations
  - `visibility.py` — PromptSet, PromptRun, AIResponse, BrandMention, Citation, SourceDomain, SourceGap operations
  - `analytics.py` — AnalyticsSnapshot, AuditEvent, AutoPipeline, VisibilitySnapshot operations
  - `campaigns.py` — Campaign, PublishedPost operations
  - `webhooks.py` — WebhookEndpoint operations
  - `integrations.py` — IntegrationSecret, RedditAccount operations
  - `system.py` — Notification, ActivityLog, UsageMetric operations

**Schemas** (`app/schemas/v1/`): Pydantic v2 request/response schemas mirroring the table operations.

**Services** (`app/services/`): Business logic layer:
- `product/pipeline.py` — orchestration of scan → opportunity → draft flow
- `product/copilot/` — LLM-driven reply and post generation (split into submodules: `analyzer.py`, `inference.py`, `keyword.py`, `llm_client.py`, `persona.py`, `reply.py`, `post.py`)
- `product/scanner.py` — Reddit scraping and opportunity detection
- `product/scoring.py` — opportunity fit scoring
- `product/entitlements.py` — plan-based feature gating and subscription management
- `product/visibility.py` — AI visibility prompt sets and citation tracking
- `product/reddit.py` — Reddit API interaction
- `product/supabase_auth.py` — Supabase Auth HTTP client (sign up, sign in, JWT verification)
- `product/discovery.py` — Subreddit discovery and analysis
- `product/relevance.py` — Relevance scoring logic (split into submodules: `scorer.py`, `audience.py`, `keyword.py`, `signals.py`, `config.py`)
- `infrastructure/llm/` — Modular LLM provider system with `LLMService` facade. **Gemini is the default provider for RedditFlow.** OpenAI (supports custom base_url), Perplexity, and Claude are supported alternatives but not required — only the active provider's API key needs to be set. Adding a new provider = one file + `register()` call.
- `utils/` — Utility modules: `security.py` (webhook validation, slugify), `encryption.py` (Fernet encryption), `slug.py`, `audit.py`, `datetime.py`

**Core** (`app/core/`): 
- `config.py` — pydantic-settings, loads from `.env`
- `exceptions.py` — custom exception hierarchy: `AppException` → `NotFoundError`, `ForbiddenError`, `ConflictError`, `AuthenticationError`, `BusinessRuleError`
- `constants/` — centralized constants: `limits.py` (rate limits, pagination, max lengths), `timeouts.py` (request timeouts, retry delays), `errors.py` (error codes, messages), `app.py` (app metadata, plan codes)
- `logging.py` — structured JSON logging configuration

**Workers**: No async task queue. Scans and generations run synchronously in-request. Background tasks use FastAPI `BackgroundTasks`.

**Database**: Supabase Postgres. All queries use the Supabase Python client (`supabase-py`) via the data access layer in `app/db/tables/`.

## Frontend Architecture

**Entry point**: `web/app/layout.tsx` — root layout wrapping children in `AuthProvider` + `Toaster`.

**Routing**: Next.js App Router. Public pages at `web/app/page.tsx` (landing), `web/app/login/`, `web/app/register/`, `web/app/reset-password/`. Authenticated app pages under `web/app/app/` with a shared layout (`app/app/layout.tsx`) that wraps in `AppShell` + `ErrorBoundary`.

**API client**: `web/lib/api.ts` — central module with `apiRequest<T>()` helper, shared types, and re-exports from domain-specific modules in `web/lib/api/` (auth, content, discovery, visibility, analytics, etc.).

**State**: Zustand stores in `web/stores/` — `auth-store.ts` (auth state, consumed by `AuthProvider`), `project-store.ts` (selected project, consumed by `useSelectedProjectId` hook), `ui-store.ts` (sidebar + notification panel toggles). `AuthProvider` (`web/components/auth/auth-provider.tsx`) wraps the tree and bridges Zustand state to React context.

**Styling**: Tailwind CSS v4 + shadcn/ui primitives built on `@base-ui/react`. Design tokens and global styles in `web/app/globals.css`. Component variants use `class-variance-authority`. Legacy plain-CSS files under `web/styles/` are being phased out.

**Components** (`web/components/`):
- `ui/` — shadcn primitives (`button.tsx`, `input.tsx`, `tabs.tsx`, `dialog.tsx`, etc.) wrapping `@base-ui/react` with Tailwind classes and CVA variants
- `app-shell.tsx` (sidebar navigation), `auth/auth-provider.tsx` (auth bootstrap), `error-boundary.tsx` (class component), `toaster.tsx`

**React 19 Notes:**
- Uses `createRoot` implicitly via Next.js 16 (no legacy `ReactDOM.render`)
- No deprecated APIs used (`getDefaultProps`, `propTypes`, `displayName` patterns avoided)
- Class components (like `ErrorBoundary`) work unchanged in React 19
- Server Components are the default; client components use `"use client"` directive

**Type Safety:**
- Error types defined in `web/types/errors.ts`: `ApiError`, `AuthError`, `ValidationError`
- Helper functions: `getErrorMessage()`, `toError()`, `isApiError()`, `isAuthError()`, `isValidationError()`
- All catch blocks use `catch (error: unknown)` with proper type guards
- Zero `: any` types in production frontend code (test files may use `as any` for mock data)

## Key Conventions

### Supabase SDK Usage (Mandatory)

**All database operations MUST use the Supabase Python SDK** via helpers in `app/db/tables/`. Never use raw SQL or direct ORM access.

**Dependency pattern in routes:**
```python
from supabase import Client
from fastapi import Depends
from app.db.supabase_client import get_supabase

@router.get("/items")
def list_items(supabase: Client = Depends(get_supabase)):
    # Use table helpers from app/db/tables/*
    items = list_items_for_workspace(supabase, workspace_id)
    return [ItemResponse.model_validate(item) for item in items]
```

**Supabase query patterns:**
```python
# Select with filter
result = db.table("opportunities").select("*").eq("project_id", pid).execute()
return result.data[0] if result.data else None

# Insert
result = db.table("projects").insert(data).execute()
return result.data[0]

# Update
result = db.table("workspaces").update(data).eq("id", wid).execute()
return result.data[0] if result.data else None

# Delete
db.table("invitations").delete().eq("id", inv_id).execute()

# Bulk insert
result = db.table("opportunities").insert(list_of_dicts).execute()

# Count (exact)
result = db.table("keywords").select("id", count="exact").eq("project_id", pid).execute()
count = result.count if result.count else 0

# IN clause
result = db.table("workspaces").select("*").in_("id", [1, 2, 3]).execute()

# Ordering and pagination
result = (
    db.table("personas")
    .select("*")
    .eq("project_id", pid)
    .order("created_at", desc=True)
    .range(0, 9)  # First 10 records
    .execute()
)
```

**Type hints for table operations:**
- Use `dict[str, Any] | None` for single record returns
- Use `list[dict[str, Any]]` for list returns
- Use `TYPE_CHECKING` imports to avoid circular dependencies

### Pydantic v2 Patterns (Mandatory)

**All request/response schemas MUST use Pydantic v2**. The project uses `pydantic>=2.8.0` and `pydantic-settings>=2.4.0`.

**Response models (from database records):**
```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Required for .model_validate()
    
    id: int
    workspace_id: int
    name: str = Field(min_length=2, max_length=255)
    slug: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
```

**Request models (from JSON body):**
```python
class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
```

**Validation with model_validator (v2 syntax):**
```python
from pydantic import model_validator

class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_secret_key: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production" and not self.supabase_url:
            raise ValueError("SUPABASE_URL is required in production.")
        return self
```

**Usage in routes:**
```python
# Validate from database record (dict)
return ProjectResponse.model_validate(project_row)

# Validate from list
return [ProjectResponse.model_validate(p) for p in projects]

# Nested validation
return DashboardResponse(
    projects=[ProjectResponse.model_validate(p) for p in projects],
    subscription=subscription_dict,
)
```

**Key Pydantic v2 changes from v1:**
- `ConfigDict(from_attributes=True)` replaces `orm_mode = True`
- `model_validate()` replaces `from_orm()`
- `model_validator(mode="after")` replaces `@validator`
- `Field()` constraints: `min_length`, `max_length`, `pattern`, `ge`, `le`, `default`

### Database Layer Conventions

**Table operation helpers** in `app/db/tables/<domain>.py` follow consistent patterns:

```python
# Naming convention
def get_<entity>_by_id(db: Client, id: int) -> dict[str, Any] | None: ...
def list_<entities>_for_<parent>(db: Client, parent_id: int) -> list[dict[str, Any]]: ...
def create_<entity>(db: Client, data: dict[str, Any]) -> dict[str, Any]: ...
def update_<entity>(db: Client, id: int, data: dict[str, Any]) -> dict[str, Any] | None: ...
def delete_<entity>(db: Client, id: int) -> None: ...
```

**Table name constants:**
```python
OPPORTUNITIES_TABLE = "opportunities"
PERSONAS_TABLE = "personas_v1"
DISCOVERY_KEYWORDS_TABLE = "discovery_keywords"
```

**Service layer pattern:**
```python
from supabase import Client
from app.db.tables.discovery import list_opportunities_for_project

def get_top_opportunities(supabase: Client, project_id: int, limit: int = 10) -> list[dict]:
    """Service function that uses Supabase client."""
    opps = list_opportunities_for_project(supabase, project_id, limit=limit)
    return sorted(opps, key=lambda x: x["score"], reverse=True)
```

### Other Conventions

- **Auth flow**: Supabase Auth with JWT Bearer tokens. Registration creates a Supabase identity + local AccountUser + workspace + membership atomically. Token carries `sub` (Supabase user ID). Workspace is resolved from membership.
- **Multi-tenancy**: Everything is scoped through `workspace_id`. Projects belong to workspaces. Most API routes require both authentication and workspace membership checks.
- **LLM**: **Gemini is the default provider for RedditFlow** (`LLM_PROVIDER=gemini`, default in `DEFAULT_LLM_PROVIDER`). Only `GEMINI_API_KEY` is required in normal operation; `OPENAI_API_KEY` and the other provider keys can be left blank. Set `LLM_PROVIDER` env var to switch to `openai`, `perplexity`, or `claude` if you need an alternative (OpenAI supports custom `OPENAI_BASE_URL` for OpenAI-compatible endpoints like Azure, Ollama, LM Studio). Always use a real LLM with a valid API key — never use mock or simulated data. The `LLMService` facade in `app/services/infrastructure/llm/service.py` is the entry point. For visibility, `VisibilityRunner` calls all configured providers.
- **Rate limiting**: In-memory rate limiter in `app/middleware.py` with per-endpoint-type limits (scan: 5/60s, generate: 10/60s, auth: 10/300s, default: 60/60s).
- **Testing**: Tests use Supabase local development or a test Supabase project. Fixtures in `conftest.py` provide `client`, `authed_client`, `authed_headers`.
- **Linting**: Ruff with `target-version = "py311"`, `line-length = 120`. Rules: E, F, W, I, N, UP, B, SIM, TCH. E501 ignored.

## Deployment

RedditFlow is a monorepo with two independent deploy targets:

- **Backend** — deployed to **Railway** from the repo root. Config: `railway.toml` (Nixpacks builder, `pip install uv && uv sync --no-dev`, `uvicorn app.main:app`). Health check: `GET /health`.
- **Frontend** (`web/`) — deployed to **Netlify**. Config: `netlify.toml` with `base = "web/"`, `command = "npm install && npm run build"`, `publish = ".next"`, and the `@netlify/plugin-nextjs` plugin. Node 20.

### Critical: do NOT add a root `package.json`

Nixpacks detects providers by the presence of marker files. If any `package.json` lands at the repo root, Nixpacks will pick the Node.js provider instead of Python and the backend build will fail with `pip: command not found`. All Node/JS config (`package.json`, `tailwind.config.*`, `postcss.config.*`, `next.config.*`, `tsconfig.json`, `components.json`) **must** live under `web/`. `nixpacks.toml` pins the Python provider as a second line of defense, but do not rely on it alone.

### Railway environment variables

Set these in the Railway dashboard (do not commit secrets):
- `DATABASE_URL` — Postgres URL (use Railway's Postgres plugin) OR use Supabase connection string
- `ENVIRONMENT=production`
- `FRONTEND_URL` — the Netlify site URL (e.g. `https://redditflow.netlify.app`) — used for CORS and password-reset redirects
- `CORS_ORIGINS_RAW` — comma-separated allowed origins, must include the Netlify URL
- `SUPABASE_URL` — Supabase project URL (e.g. `https://xxxxx.supabase.co`)
- `SUPABASE_PUBLISHABLE_KEY` — Supabase anon/public key
- `SUPABASE_SECRET_KEY` — Supabase service role key
- `SUPABASE_JWT_SECRET` — Supabase JWT secret for local verification
- `GEMINI_API_KEY` — **required** (Gemini is the default LLM provider)
- `LLM_PROVIDER` — default is `gemini`. Only set this to `openai` / `perplexity` / `claude` if you're switching providers.
- `OPENAI_API_KEY` — **not required** unless `LLM_PROVIDER=openai`. Leave unset for Gemini-only deployments.
- `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY` — likewise optional alternatives.
- Optional: `ENCRYPTION_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `SMTP_*`

### Netlify environment variables

Set these in the Netlify dashboard under Site settings → Environment variables:
- `NEXT_PUBLIC_API_BASE_URL` — the Railway backend URL (e.g. `https://redditflow-api.up.railway.app`) — consumed by `web/lib/api.ts:1`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

### Cross-origin wiring

Because the two services live on different domains, the frontend and backend URLs must reference each other:
1. After the first Railway deploy, copy the Railway service URL into Netlify's `NEXT_PUBLIC_API_BASE_URL`.
2. After the first Netlify deploy, copy the Netlify site URL into Railway's `FRONTEND_URL` and `CORS_ORIGINS_RAW`.
3. Redeploy both once so each side picks up the other's URL.

## Refactoring History

### 2026-04-11: Comprehensive Code Quality Refactor

**Completed:**
- **Type Safety**: Created Pydantic v2 models for all database tables in `app/models/`
- **Constants Extraction**: Moved magic numbers/strings to `app/core/constants/` (limits, timeouts, errors, app metadata)
- **Module Splitting**: 
  - Split `copilot.py` (646 lines) → `copilot/` package with focused modules
  - Split `relevance.py` (1,276 lines) → `relevance/` package with scorer, audience, keyword, signals, config
  - Eliminated `other.py` dumping ground → split into `campaigns.py`, `webhooks.py`, `integrations.py`, `system.py`
- **Service Reorganization**:
  - `llm.py` → `infrastructure/llm/`
  - `security.py`, `encryption.py` → `utils/`
  - `logging_config.py` → `core/logging.py`
- **Frontend Type Safety**: Eliminated all `: any` types, created error type hierarchy in `web/types/errors.ts`
- **Documentation**: Added comprehensive docstrings to key service modules

**Verification:**
- All 76 backend tests pass
- Frontend builds successfully with TypeScript type checking
- Zero `: any` types in production frontend code (only test files use `as any` for mock data)

### 2026-04-11: Modular LLM Provider System

**Completed:**
- **Modular LLM architecture**: Replaced 3 disconnected LLM systems with a unified provider system:
  - `infrastructure/llm/base.py` — `LLMProvider` Protocol with `chat_json()` and `chat_text()`
  - `infrastructure/llm/providers/` — One file per provider: `openai_provider.py`, `gemini_provider.py`, `perplexity_provider.py`, `claude_provider.py`
  - `infrastructure/llm/providers/_registry.py` — Lightweight registry with `register()`, `get_provider()`, `get_configured_providers()`
  - `infrastructure/llm/service.py` — `LLMService` (single-provider facade) + `VisibilityRunner` (multi-provider facade)
- **Gemini as default** (changed from OpenAI on 2026-04-15 — see commit on branch `claude/pedantic-mirzakhani`). OpenAI provider still supported as an alternative and retains `OPENAI_BASE_URL` support for custom endpoints (Azure, Ollama, LM Studio, Together AI), but is no longer required.
- **Backward compatible**: `LLMClient` refactored to thin adapter, zero changes to consumer modules
- **Visibility unified**: `ModelRunner` replaced by `VisibilityRunner`, all 4 providers use shared abstraction
- **Config**: `LLM_PROVIDER` env var selects active provider. Per-provider API key/model/base_url settings.

**Verification:**
- 74 tests pass (2 pre-existing failures unrelated to LLM changes)
- Lint clean on all modified files
- Import chain verified: registry populated with all providers on startup

## Critical Reference Files

Study these files to understand the correct patterns:

**Supabase SDK patterns:**
- `app/db/supabase_client.py` — Singleton client and FastAPI dependency
- `app/db/tables/discovery.py` — Comprehensive table operations (personas, keywords, opportunities)
- `app/db/tables/workspaces.py` — Complex queries with memberships, invitations, subscriptions
- `app/db/tables/projects.py` — Project and brand profile operations

**Pydantic v2 patterns:**
- `app/schemas/v1/projects.py` — Clean request/response models
- `app/schemas/v1/discovery.py` — Field validation and response models
- `app/core/config.py` — Settings with `model_validator`

**Route handler patterns:**
- `app/api/v1/routes/projects.py` — Complete CRUD with proper dependencies
- `app/api/v1/deps.py` — Auth and workspace helpers

**Frontend Reference Files:**
- `web/app/layout.tsx` — Root layout with AuthProvider + ThemeProvider
- `web/components/auth/auth-provider.tsx` — Auth state bootstrap with Supabase session sync
- `web/components/app/app-shell.tsx` — Main app shell with sidebar navigation
- `web/stores/auth-store.ts` — Zustand auth store (token, user, workspace)
- `web/stores/project-store.ts` — Zustand project store (selected project ID)
- `web/lib/supabase.ts` — Lazy Supabase client initialization (browser-only)
- `web/lib/api.ts` — API client with `apiRequest<T>()` helper

**LLM Provider System:**
- `app/services/infrastructure/llm/base.py` — `LLMProvider` Protocol definition
- `app/services/infrastructure/llm/service.py` — `LLMService` + `VisibilityRunner` facades
- `app/services/infrastructure/llm/providers/_registry.py` — Provider registry and factory
- `app/services/infrastructure/llm/providers/gemini_provider.py` — Gemini via httpx (**primary/default provider**)
- `app/services/infrastructure/llm/providers/openai_provider.py` — OpenAI (optional alternative, custom base_url support)
- `app/services/product/copilot/llm_client.py` — Backward-compatible adapter over LLMService
