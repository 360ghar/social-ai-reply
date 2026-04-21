# RedditFlow

Hosted Reddit opportunity intelligence built on `FastAPI + Postgres/SQLite + Next.js`.

RedditFlow is a hosted web app for finding relevant Reddit posts, reviewing good-fit communities, and drafting helpful replies without auto-posting.

## Product Policy

RedditFlow currently does **not** enforce customer-facing query limits, scan quotas, generation caps, seat caps, or plan-based usage ceilings. In the initial phase, unrestricted product usage is an intentional product and system-design decision by the team.

Any backend rate limiting that exists is there only for infrastructure protection and abuse control. It should not be interpreted as a commercial product limit.

This repo now contains two product layers:

- `app/`: production-oriented backend APIs, auth, discovery, scan orchestration, drafting, billing/subscription scaffolding, secrets, webhooks, and legacy Instagram services.
- `web/`: hosted browser frontend for marketing, auth, the step-by-step app flow, optional advanced settings, and plan management.

## What Is Implemented

- JWT auth with workspace bootstrap
- Project, brand profile, persona, keyword, subreddit, scan, opportunity, prompt, webhook, secret, invitation, billing, and redemption models
- New `/v1` API surface for the hosted SaaS
- Website analysis, keyword generation, subreddit discovery, opportunity scoring, reply drafting, and post drafting
- Browser frontend in Next.js wired to the new backend
- Health and readiness endpoints
- Legacy Instagram backend kept in place and isolated from the new product surface

## Backend Setup

```bash
cp .env.example .env
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

The default `.env.example` uses SQLite so local setup works immediately. For production, switch `DATABASE_URL` to Postgres.

Backend app:

- API docs: `http://localhost:8000/docs`
- Health: `GET /health`
- Ready: `GET /ready`

## Frontend Setup

```bash
cd web
npm install
npm run dev
```

Frontend app:

- Web app: `http://localhost:3000`

## Important Environment Variables

- `DATABASE_URL`
- `JWT_SECRET`
- `ENCRYPTION_KEY`
- `OPENAI_API_KEY`
- `FRONTEND_URL`
- `CORS_ORIGINS_RAW`
- `REDDIT_USER_AGENT`

## Tests

```bash
uv run pytest -q
cd web && npm run build
```

## Notes

- The new SaaS routes live under `/v1`.
- Posting is intentionally manual. The product generates research and drafts; it does not auto-post to Reddit.
- The initial product rollout intentionally has no customer-facing usage caps or quotas.
- The legacy Instagram endpoints are still available for existing local workflows, but they are not part of the new hosted v1 product surface.
