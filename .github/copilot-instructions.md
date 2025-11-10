## Copilot / AI Agent Instructions for Potentia (concise)

This project is a FastAPI backend for an AI-powered collaborative canvas. The goal of this file is to give an AI coding agent the minimal, concrete context needed to be productive quickly.

- Big picture
  - Backend (FastAPI) lives under `backend/` and is the primary code surface. The app entry is `backend/app/main.py` which wires routers, lifespan startup/shutdown, scheduler jobs and background workers.
  - Persistence: Supabase/Postgres (use `DATABASE_URL` / Supabase keys in `backend/app/core/config.py`). Vector support uses `pgvector`.
  - Pub/Sub & scaling: Redis is used for rate limiting and pub/sub (see `backend/app/services/redis_pubsub.py` and `docker-compose.yml`).
  - AI integration: Google Gemini + other models; keys/config are set in `backend/app/core/config.py` (GEMINI_* vars). Prompts and templates live in `backend/app/prompts/`.

- How to run (dev)
  - Copy `.env.example` → `.env` and fill required secrets (DATABASE_URL, SUPABASE_* keys, GEMINI_API_KEY, JWT_SECRET, etc.). `pydantic_settings` loads `.env` in `Settings`.
  - Quick start with Docker (recommended for parity):
    - `docker-compose up --build` (root-level `docker-compose.yml` builds `./backend` and runs Redis).
  - Local dev (no Docker):
    - Ensure Postgres/Supabase and Redis are reachable.
    - Start with Uvicorn: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` from `backend/`.

- Tests & lint
  - Tests live under `backend/tests/`. Run pytest from `backend/` when dependencies are installed.
  - The repo does not enforce a specific linter config here; follow existing logging and import patterns.

- Key patterns & conventions
  - Async-first: use `async` endpoints, `asyncpg` pool (`backend/app/db/asyncpg_pool.py`), and `redis` async client patterns.
  - Lifespan management: startup/shutdown logic is centralized in `backend/app/main.py` via `lifespan()` — modify there for global lifecycle actions (connect/disconnect DB, Redis, workers, scheduler).
  - Background jobs: APScheduler + long-running workers live in `backend/app/workers/` (embedding, rebalance, cleanup). Stop/start of workers is managed in `main.py` lifespan.
  - Services layer: `backend/app/services/` contains domain logic (chat, canvas, schedule, etc.). Prefer adding helpers into services, keep endpoints thin.
  - Prompts: `backend/app/prompts/` contains templates and text files used by AI. Prefer editing templates here rather than hardcoding in services.

- Observability
  - OpenTelemetry is configured in `main.py`. The code instruments FastAPI & HTTPX when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
  - Logging config is declared in `main.py` (LOGGING_CONFIG) — follow the existing logger names ("app", "uvicorn", "httpx").

- Environment & secrets
  - Required env vars are defined in `backend/app/core/config.py` (DATABASE_URL, SUPABASE_*, GEMINI_*, JWT_SECRET, REDIS_URL, etc.). Do not hardcode secrets in code.

- Integration touchpoints to be careful about
  - Supabase: migrations exist in `backend/app/db/migrations/`; schema changes must align with `schema.sql` and Supabase config.
  - Redis Pub/Sub: scaling WebSocket/SSE relies on `redis_pubsub` service — changes here affect real-time features.
  - Worker interactions: `asyncpg` LISTEN/NOTIFY is used by some workers (rebalance); ensure connection pool behavior is preserved when refactoring.

- When making changes
  - Run unit tests in `backend/tests/` after edits.
  - Update README (`backend/README.md`) if you add or change environment variables or runtime commands.

If anything above is unclear or you want a longer/shorter version, tell me which sections to expand or examples to include.
