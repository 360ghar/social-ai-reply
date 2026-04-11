# RedditFlow — Project Context

## Project Overview

**RedditFlow** is a hosted SaaS for finding relevant Reddit posts, scoring opportunities, and drafting helpful replies. All posting is **manual** — nothing is auto-posted to Reddit. It provides a FastAPI backend with Supabase Auth + Postgres, and a Next.js 16 frontend.

### Tech Stack
| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11+, FastAPI, Supabase SDK, Pydantic v2 |
| **Frontend** | Next.js 16, React 19, Tailwind CSS v4, shadcn/ui, Zustand |
| **Auth** | Supabase Auth (JWT Bearer) |
| **Database** | Supabase Postgres |
| **LLM** | OpenAI (primary, custom base_url), Gemini, Perplexity, Claude |
| **Deploy** | Backend → Railway, Frontend → Netlify |

### Architecture
- **Backend** (`app/`): FastAPI app with layered structure (routes → services → db tables). All APIs live under `/v1`.
- **Frontend** (`web/`): Next.js App Router with authenticated layout (`web/app/app/`) and public pages (`web/app/`).
- **Multi-tenancy**: Everything scoped by `workspace_id`. Projects belong to workspaces. Most routes require auth + workspace membership.

## Building and Running

### Backend
```bash
cp .env.example .env
uv sync --extra dev
uv run uvicorn app.main:app --reload      # dev server at :8000
uv run pytest -q                           # run all tests
uv run ruff check app/ tests/              # lint
uv run ruff check --fix app/ tests/        # auto-fix lint issues
```

### Frontend
```bash
cd web && npm install
npm run dev       # dev server at :3000
npm run build     # type-check + production build
```

### API Docs
- Swagger UI: `http://localhost:8000/docs`
- Health check: `GET /health`
- Readiness: `GET /ready`

## Key Directories

```
├── app/                          # Backend (FastAPI)
│   ├── api/v1/routes/            # Domain route modules (auth, projects, discovery, etc.)
│   ├── api/v1/deps.py            # Auth, workspace, project dependencies
│   ├── core/                     # Config, exceptions, logging
│   ├── db/                       # Supabase client + table helpers
│   │   ├── supabase_client.py    # Singleton client + get_supabase() dep
│   │   └── tables/               # Typed query helpers per domain
│   ├── schemas/v1/               # Pydantic v2 request/response models
│   ├── services/                 # Business logic (pipeline, LLM, scanner, scoring, etc.)
│   │   ├── infrastructure/llm/   # Modular LLM provider system
│   │   │   ├── base.py           # LLMProvider Protocol
│   │   │   ├── service.py        # LLMService + VisibilityRunner facades
│   │   │   └── providers/        # One file per provider (openai, gemini, perplexity, claude)
│   │   └── product/              # Product services (copilot, pipeline, visibility, etc.)
│   └── main.py                   # App entry point, middleware, health checks
├── web/                          # Frontend (Next.js)
│   ├── app/                      # App Router pages
│   ├── components/               # UI components (shadcn, app-shell, etc.)
│   ├── lib/                      # API client + helpers
│   ├── stores/                   # Zustand state stores
│   └── package.json              # Frontend dependencies
├── tests/                        # Backend tests
├── railway.toml                  # Railway deploy config
├── netlify.toml                  # Netlify deploy config
└── pyproject.toml                # Python dependencies + tool config
```

## Development Conventions

### Backend Patterns
- All DB queries use Supabase Python SDK via `app/db/tables/*` helpers
- Route handlers use `supabase: Client = Depends(get_supabase)`
- Pydantic v2 models: use `ConfigDict(from_attributes=True)` for DB responses
- Linting: Ruff, `target-version = "py311"`, `line-length = 120`
- Error handling: Custom exception hierarchy (`AppException` → `NotFoundError`, `ForbiddenError`, etc.)

### LLM Provider System
- **Always use a real LLM with a valid API key — never use mock or simulated data.**
- OpenAI is the default provider. Set `OPENAI_BASE_URL` for custom endpoints (Azure, Ollama, LM Studio).
- Set `LLM_PROVIDER` env var to select provider: `openai`, `gemini`, `perplexity`, `claude`.
- Entry point: `LLMService` facade in `app/services/infrastructure/llm/service.py`
  - `call_json(system_prompt, user_content, temperature)` — structured JSON output (copilot)
  - `call_text(prompt, system_message, temperature)` — raw text output (visibility)
- For AI visibility tracking: `VisibilityRunner` calls all configured providers simultaneously.
- Adding a new provider: create one file in `providers/`, implement `from_settings()` + `chat_json()` + `chat_text()`, call `register("name", Class)`.

### Frontend Patterns
- API calls use `apiRequest<T>()` helper in `web/lib/api.ts`
- State managed via Zustand stores (`auth-store`, `project-store`, `ui-store`)
- React 19 compatible — no deprecated APIs in use
- Tailwind CSS v4 with CVA variants for component styling

### Rate Limiting
In-memory rate limiter in `app/middleware.py`:
- Scan: 5 req / 60s
- Generate: 10 req / 60s
- Auth: 10 req / 300s
- Default: 60 req / 60s

## Important Environment Variables

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SECRET_KEY` | Supabase service role key |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase anon key (frontend) |
| `SUPABASE_JWT_SECRET` | JWT verification secret |
| `LLM_PROVIDER` | LLM provider to use (default: `openai`) |
| `OPENAI_API_KEY` | OpenAI API key (required if LLM_PROVIDER=openai) |
| `OPENAI_MODEL` | OpenAI model (default: `gpt-4.1-mini`) |
| `OPENAI_BASE_URL` | Custom OpenAI-compatible endpoint (optional) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GEMINI_MODEL` | Gemini model (default: `gemini-2.0-flash`) |
| `PERPLEXITY_API_KEY` | Perplexity API key (for visibility) |
| `ANTHROPIC_API_KEY` | Anthropic/Claude API key (for visibility) |
| `FRONTEND_URL` | Frontend URL (for CORS + redirects) |
| `CORS_ORIGINS_RAW` | Comma-separated allowed origins |
| `REDDIT_USER_AGENT` | Reddit API user agent string |
| `STRIPE_*` | Stripe billing integration |
| `SMTP_*` | Email sending configuration |

## Deployment

### Backend (Railway)
- Deploy from repo root
- Nixpacks build: `pip install uv && uv sync --no-dev`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`
- Health check: `/health`

### Frontend (Netlify)
- Deploy from `web/` directory
- Build: `npm install && npm run build`
- Publish: `.next`
- Uses `@netlify/plugin-nextjs`

### Cross-Origin Wiring
After first deploys:
1. Set Netlify's `NEXT_PUBLIC_API_BASE_URL` → Railway URL
2. Set Railway's `FRONTEND_URL` / `CORS_ORIGINS_RAW` → Netlify URL
3. Redeploy both services

**Important:** Do NOT add a root `package.json`. Nixpacks will pick Node.js instead of Python and break the backend build.
