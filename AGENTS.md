# AGENTS.md

## Project Overview

RedditFlow is a hosted SaaS for finding relevant Reddit posts, scoring opportunities, and drafting helpful replies. All posting is manual — nothing is auto-posted to Reddit.

## Commands

### Backend
```bash
cp .env.example .env
uv sync --extra dev
uv run uvicorn app.main:app --reload      # dev server at :8000
uv run pytest -q                           # all tests
uv run pytest tests/unit/test_security.py -q  # single file
uv run ruff check app/ tests/              # lint
uv run ruff check --fix app/ tests/        # auto-fix lint
uv run python scripts/init_db.py           # manual DB init
```

### Frontend
```bash
cd web && npm install
npm run dev       # dev server at :3000
npm run build     # type-check + production build (serves as the test step)
```

## Architecture

### Backend (`app/`)

FastAPI + SQLAlchemy + JWT auth. Entry point: `app/main.py` — creates app, registers middleware (request tracing + rate limiting), mounts v1 routes, auto-creates DB tables on startup.

**Layered structure:**
- **Routes** (`app/api/v1/routes/`) — domain modules (auth, projects, discovery, drafts, scans, billing, webhooks, etc.). Aggregated in `__init__.py`. All live under `/v1`.
- **Dependencies** (`app/api/v1/deps.py`) — `get_current_user`, `get_current_workspace`, `get_project`, `get_active_project`, `ensure_default_prompts`. All authenticated endpoints use these.
- **Schemas** (`app/schemas/v1/`) — Pydantic v2 request/response models.
- **Models** (`app/db/models/`) — SQLAlchemy ORM by domain, re-exported via `__init__.py`.
- **Services** (`app/services/`) — business logic:
  - `product/pipeline.py` — scan → opportunity → draft orchestration
  - `product/copilot.py` — LLM-driven reply/post generation
  - `product/scanner.py` — Reddit scraping and opportunity detection
  - `product/scoring.py` — opportunity fit scoring
  - `product/entitlements.py` — plan-based feature gating
  - `product/visibility.py` — AI visibility prompt sets and citation tracking
  - `product/reddit.py` — Reddit API interaction
  - `product/security.py` — JWT encode/decode, password hashing
  - `product/encryption.py` — symmetric encryption for stored secrets
  - `llm.py` — LLM provider abstraction (Gemini primary, Mock fallback)
- **Core** (`app/core/`) — `config.py` (pydantic-settings), `exceptions.py` (custom hierarchy: `AppException` → `NotFoundError`, `ForbiddenError`, `ConflictError`, `AuthenticationError`, `BusinessRuleError`).

**Database:** SQLite for dev, Postgres for production. Session via `app/db/session.py` generator dependency (`get_db`).

### Frontend (`web/`)

Next.js 16 + React 18 + Tailwind CSS v4 + shadcn/ui (on `@base-ui/react`) + Zustand.

- **Routing:** App Router. Public: `web/app/page.tsx`, `login/`, `register/`, `reset-password/`. Authenticated: `web/app/app/` with shared layout wrapping `AppShell` + `ErrorBoundary`.
- **API client:** `web/lib/api.ts` — `apiRequest<T>()` helper + domain modules in `web/lib/api/`.
- **State:** Zustand stores in `web/stores/` (`auth-store`, `project-store`, `ui-store`). Auth state is managed via `useAuthStore` (`web/stores/auth-store.ts`) and consumed through the `useAuth` hook exported from `web/components/auth/auth-provider.tsx`. `useSelectedProjectId` hook reads `project-store`.
- **Styles:** Tailwind v4 + CVA variants. Tokens/globals in `web/app/globals.css`. Legacy `web/styles/` plain CSS is being phased out.
- **Components:** `web/components/ui/` — shadcn primitives (`button`, `input`, `tabs`, `dialog`, ...). `web/components/` — `app-shell.tsx`, `auth/auth-provider.tsx`, `error-boundary.tsx`, `toaster.tsx`.

## Key Conventions

- **Auth:** JWT Bearer tokens. Registration creates user + workspace + membership atomically. Token carries `sub` (user ID). Workspace resolved from membership, not token.
- **Multi-tenancy:** Everything scoped by `workspace_id`. Projects belong to workspaces. Most routes require auth + workspace membership.
- **LLM:** Gemini is primary. Set `USE_MOCK_LLM=true` or omit `GEMINI_API_KEY` for `MockLLMProvider` (deterministic, domain-aware responses based on business description keywords).
- **Rate limiting:** In-memory in `app/middleware.py` — scan: 5/60s, generate: 10/60s, auth: 10/300s, default: 60/60s.
- **Testing:** In-memory SQLite with foreign keys. `conftest.py` fixtures: `client`, `authed_client`, `authed_headers` (auto-register user, inject auth headers).
- **Linting:** Ruff, `target-version = "py311"`, `line-length = 120`. Rules: E, F, W, I, N, UP, B, SIM, TCH. E501 ignored.

## Environment Variables

Key vars (see `.env.example` for full list): `DATABASE_URL`, `JWT_SECRET`, `ENCRYPTION_KEY`, `GEMINI_API_KEY`, `FRONTEND_URL`, `CORS_ORIGINS_RAW`, `REDDIT_USER_AGENT`.
