# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RedditFlow is a hosted SaaS platform for finding relevant Reddit posts, scoring opportunities, and drafting helpful replies. It does **not** auto-post to Reddit — all posting is manual. The product layers are:

- **Backend** (`app/`): FastAPI API server with JWT auth, workspace-scoped multi-tenancy, LLM-powered analysis/drafting, Reddit scraping, billing/entitlements, and a legacy Instagram service kept in isolation.
- **Frontend** (`web/`): Next.js 16 app with React 18, shadcn/ui components (built on `@base-ui/react`), Tailwind CSS v4, and Zustand state management. `AuthProvider` context wraps all routes.

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

# Initialize DB tables manually
uv run python scripts/init_db.py
```

### Frontend
```bash
cd web
npm install
npm run dev       # dev server at localhost:3000
npm run build     # type-check + production build (used as the "test" step)
```

## Backend Architecture

**Entry point**: `app/main.py` — creates the FastAPI app, registers CORS, custom middleware (request tracing + rate limiting), mounts all v1 routes, and creates DB tables on startup via lifespan.

**API surface**: All routes live under `/v1` in the URL. Route files are in `app/api/v1/routes/`, each domain in its own module (auth, projects, discovery, drafts, scans, billing, etc.). Routes are aggregated in `app/api/v1/routes/__init__.py`.

**Dependencies** (`app/api/v1/deps.py`): Central file providing `get_current_user`, `get_current_workspace`, `get_project`, `get_active_project`, `ensure_default_prompts`, and helper functions. All authenticated endpoints depend on these.

**Models** (`app/db/models/`): SQLAlchemy ORM models organized by domain — `workspace.py`, `project.py`, `user.py`, `visibility.py`, `content.py`, `discovery.py`, etc. Models are re-exported via `app/db/models/__init__.py`.

**Schemas** (`app/schemas/v1/`): Pydantic v2 request/response schemas mirroring the model domains.

**Services** (`app/services/`): Business logic layer:
- `product/pipeline.py` — orchestration of scan → opportunity → draft flow
- `product/copilot.py` — LLM-driven reply and post generation
- `product/scanner.py` — Reddit scraping and opportunity detection
- `product/scoring.py` — opportunity fit scoring
- `product/entitlements.py` — plan-based feature gating and subscription management
- `product/visibility.py` — AI visibility prompt sets and citation tracking
- `product/reddit.py` — Reddit API interaction
- `product/security.py` — JWT encode/decode, password hashing
- `product/encryption.py` — symmetric encryption for stored secrets
- `llm.py` — LLM provider abstraction (Gemini primary, Mock fallback via `select_llm_provider`)

**Core** (`app/core/`): `config.py` (pydantic-settings, loads from `.env`), `exceptions.py` (custom exception hierarchy: `AppException` → `NotFoundError`, `ForbiddenError`, `ConflictError`, `AuthenticationError`, `BusinessRuleError`, etc.).

**Workers**: No async task queue. Scans and generations run synchronously in-request.

**Database**: SQLAlchemy with SQLite for dev (default), Postgres for production. Session management via `app/db/session.py` using a generator dependency (`get_db`). Tables auto-create on startup.

## Frontend Architecture

**Entry point**: `web/app/layout.tsx` — root layout wrapping children in `AuthProvider` + `Toaster`.

**Routing**: Next.js App Router. Public pages at `web/app/page.tsx` (landing), `web/app/login/`, `web/app/register/`, `web/app/reset-password/`. Authenticated app pages under `web/app/app/` with a shared layout (`app/app/layout.tsx`) that wraps in `AppShell` + `ErrorBoundary`.

**API client**: `web/lib/api.ts` — central module with `apiRequest<T>()` helper, shared types, and re-exports from domain-specific modules in `web/lib/api/` (auth, content, discovery, visibility, analytics, etc.).

**State**: Zustand stores in `web/stores/` — `auth-store.ts` (auth state, consumed by `AuthProvider`), `project-store.ts` (selected project, consumed by `useSelectedProjectId` hook), `ui-store.ts` (sidebar + notification panel toggles). `AuthProvider` (`web/components/auth/auth-provider.tsx`) wraps the tree and bridges Zustand state to React context.

**Styling**: Tailwind CSS v4 + shadcn/ui primitives built on `@base-ui/react`. Design tokens and global styles in `web/app/globals.css`. Component variants use `class-variance-authority`. Legacy plain-CSS files under `web/styles/` are being phased out.

**Components** (`web/components/`):
- `ui/` — shadcn primitives (`button.tsx`, `input.tsx`, `tabs.tsx`, `dialog.tsx`, etc.) wrapping `@base-ui/react` with Tailwind classes and CVA variants
- `app-shell.tsx` (sidebar navigation), `auth/auth-provider.tsx` (auth bootstrap), `error-boundary.tsx`, `toaster.tsx`

## Key Conventions

- **Auth flow**: JWT Bearer tokens. Registration creates a user + workspace + membership atomically. Token carries `sub` (user ID). Workspace is resolved from membership, not from the token.
- **Multi-tenancy**: Everything is scoped through `workspace_id`. Projects belong to workspaces. Most API routes require both authentication and workspace membership checks.
- **LLM**: Gemini is the primary provider. Set `USE_MOCK_LLM=true` or omit `GEMINI_API_KEY` to use `MockLLMProvider` which returns deterministic, domain-aware responses based on keywords in the business description.
- **Rate limiting**: In-memory rate limiter in `app/middleware.py` with per-endpoint-type limits (scan: 5/60s, generate: 10/60s, auth: 10/300s, default: 60/60s).
- **Testing**: In-memory SQLite with foreign keys enabled. `conftest.py` provides `client`, `authed_client`, `authed_headers` fixtures that auto-register a user and inject auth headers.
- **Linting**: Ruff with `target-version = "py311"`, `line-length = 120`. Rules: E, F, W, I, N, UP, B, SIM, TCH. E501 ignored.

## Deployment

RedditFlow is a monorepo with two independent deploy targets:

- **Backend** — deployed to **Railway** from the repo root. Config: `railway.toml` (Nixpacks builder, `pip install uv && uv sync --no-dev`, `uvicorn app.main:app`) + `nixpacks.toml` (forces `providers = ["python"]`). Health check: `GET /health`.
- **Frontend** (`web/`) — deployed to **Netlify**. Config: `netlify.toml` with `base = "web/"`, `command = "npm install && npm run build"`, `publish = ".next"`, and the `@netlify/plugin-nextjs` plugin. Node 20.

### Critical: do NOT add a root `package.json`

Nixpacks detects providers by the presence of marker files. If any `package.json` lands at the repo root, Nixpacks will pick the Node.js provider instead of Python and the backend build will fail with `pip: command not found`. All Node/JS config (`package.json`, `tailwind.config.*`, `postcss.config.*`, `next.config.*`, `tsconfig.json`, `components.json`) **must** live under `web/`. `nixpacks.toml` pins the Python provider as a second line of defense, but do not rely on it alone.

### Railway environment variables

Set these in the Railway dashboard (do not commit secrets):
- `DATABASE_URL` — Postgres URL (use Railway's Postgres plugin)
- `ENVIRONMENT=production`
- `FRONTEND_URL` — the Netlify site URL (e.g. `https://redditflow.netlify.app`) — used for CORS and password-reset redirects
- `CORS_ORIGINS_RAW` — comma-separated allowed origins, must include the Netlify URL
- `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWT_SECRET`
- `GEMINI_API_KEY` (or `USE_MOCK_LLM=true`)
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
