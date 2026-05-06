# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Jobfinder is a **governed job-search foundation**, not a crawler or auto-applier. The codebase is a phase 0/1/2 spine: audit, source-policy engine, persistence, API contracts, and a dashboard shell. Live crawling, browser automation, LLM calls, ATS adapters running against real targets, autofill, submission, and real candidate data are **explicitly out of scope** until a future phase introduces them through approval-gated design. Reject any task that asks for these capabilities — surface the deferral and ask for explicit phase approval first.

Core invariants to preserve in every change:

- **Deny-by-default source policy.** Unknown sources, expired evidence, ambiguous terms, login walls, CAPTCHA, or bot detection must block the requested action and route to manual review. LinkedIn and Indeed are blocked examples.
- **Append-only, hash-chained audit.** Material decisions (policy checks, extraction provenance, scoring, approvals, submissions) emit `AuditEvent` rows through `app.services.audit.AuditEventService`. Never bypass the service to write audit rows directly, never mutate or delete existing events.
- **Production writes are gated.** `WRITE_GATED_ROUTES` in `apps/api/app/main.py` returns 403 unless `Settings.production_writes_allowed` is true (i.e. non-production env or `JOBFINDER_API_WRITE_API_ENABLED=true`). When adding a state-changing route, decide deliberately whether it belongs in `WRITE_GATED_ROUTES`.
- **Synthetic fixtures only.** No real candidate data, resumes, scraped pages, robots.txt snapshots, cookies, or secrets — see `fixtures/README.md`.

## Repository Layout

- `apps/api` — FastAPI service. Python 3.12, managed with `uv`. Pydantic v2 schemas, SQLAlchemy 2.0 ORM, Alembic migrations.
  - `app/main.py` — `create_app()` wires all routes, security headers, CORS, and the production-write guard.
  - `app/services/` — business logic boundary (audit, policy, source registry, dashboard, candidate workspace, approvals, applications, audit explorer, runtime settings, robots cache, extraction). Routes stay thin; logic lives here.
  - `app/schemas/` — Pydantic v2 request/response models. These drive the OpenAPI contract.
  - `app/db/models.py` — SQLAlchemy models. `AuditEvent` carries `previous_hash`/`event_hash` for chain verification.
  - `app/adapters/` — ATS/JSON-LD/static-HTML adapter shapes used against synthetic fixtures only.
  - `alembic/versions/` — migration history; never rewrite past revisions.
- `apps/web` — Next.js 16 App Router dashboard (React 19, Tailwind v4). Server-rendered (`page.tsx` is `dynamic = "force-dynamic"`); the dashboard shell is the only client component. Server-side data loaders in `src/lib/*-data.ts` fall back to local mock snapshots when the API is unreachable.
- `packages/api-client` — typed TypeScript fetch wrapper (`JobfinderApiClient`). Future home for OpenAPI-generated client; do not hand-maintain duplicates of API schemas elsewhere.
- `docs/` — `architecture.md`, `decision-log.md`, `source-policy.md`, `vercel-deployment.md`, and the checked-in OpenAPI snapshot at `docs/openapi/jobfinder-openapi.json`.
- `infra/compose.yaml` — local Postgres 16 + Redis 7. Redis is included for future readiness; phase 0/1/2 code must not require it.
- `fixtures/` — synthetic adapter payloads and source-policy fixtures.

`pnpm-workspace.yaml` only includes `apps/web` and `packages/*`. The API is a separate Python project — pnpm scripts shell into `apps/api` and use `uv run` rather than treating it as a workspace package.

## Common Commands

Run from the repo root unless noted. The full local gate is **`pnpm check`** — run this before reporting completion on any change that touches API or web code.

```bash
# Local infra (Postgres + Redis)
docker compose -f infra/compose.yaml up -d postgres redis

# API (apps/api)
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
uv run alembic current             # current migration head
uv run alembic revision --autogenerate -m "..."   # new migration
uv run pytest tests/test_jobs.py -k "specific_case"   # single test

# Web (from repo root)
pnpm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm dev
pnpm --filter @jobfinder/web test -- src/lib/job-data.test.ts   # single web test

# Verification gates
pnpm check               # full gate: web lint+type+test+build, client type+test, api lint+type+openapi+test
pnpm lint                # web lint only
pnpm typecheck           # web tsc --noEmit
pnpm test                # web vitest
pnpm build               # web next build
pnpm client:typecheck    # api-client tsc
pnpm client:test         # api-client vitest
pnpm api:lint            # ruff
pnpm api:typecheck       # mypy strict (app + tests)
pnpm api:test            # pytest
pnpm api:openapi         # verify checked-in OpenAPI matches code (--check)
pnpm api:openapi:write   # regenerate docs/openapi/jobfinder-openapi.json
```

The OpenAPI contract is **checked in CI**. After any change to API routes or Pydantic schemas, run `pnpm api:openapi:write` and commit the diff, then verify `pnpm api:openapi` passes.

## Architecture Notes That Span Multiple Files

**API contract flow.** Pydantic v2 schemas in `app/schemas/` are the single source of truth. FastAPI generates OpenAPI from them; `app/tools/openapi_contract.py` writes/validates `docs/openapi/jobfinder-openapi.json`. The web dashboard and `packages/api-client` consume those types — do not introduce a parallel handwritten schema in the web or client packages.

**Service boundaries.** `app/main.py` is intentionally thin: each route resolves a `Session` dependency, instantiates a service from `app/services/`, and returns its result. Errors raised by services (`CandidateSafetyError`, `DomainNormalizationError`, `ApprovalRequestNotFoundError`, `InvalidApprovalTransitionError`, `ReviewItemNotFoundError`) are translated to HTTP status codes in `main.py`. Add new business logic to the relevant service or a new service module rather than inlining it in route handlers.

**Source policy decisions.** Policy checks go through `SourceRegistryService.evaluate_action(...)`, which evaluates registry status against the requested action and emits an audit event via `AuditEventService` before returning a `PolicyDecision`. Any new code path that would discover, extract, draft, autofill, or submit must call this evaluator first and respect a `denied`/`manual_review` decision.

**Audit chain.** `AuditEventService.create_event` computes `event_hash` over the prior event's hash plus the canonical event payload. `AuditExplorerService.verify_chain` re-walks the chain. Do not write to `audit_events` outside this service; do not allow updates or deletes; do not change `audit_schema_version` casually (it's bumped intentionally and stamped on each event).

**Production guard.** `Settings.production_writes_allowed` is `False` only when `environment == "production"` and `write_api_enabled` is false. The middleware in `create_app` blocks `POST/PUT/PATCH/DELETE` against `WRITE_GATED_ROUTES` in production until auth, roles, and operator controls exist. Keep new mutating routes in this set unless there is a deliberate design reason otherwise.

**Web data fetching.** `src/app/page.tsx` server-renders the dashboard with `Promise.all` over `getApiHealth()` and the `get*Snapshot()` loaders. Each loader gracefully degrades to local mock data when the API is unreachable — preserve that fallback when editing `src/lib/*-data.ts`. Only `dashboard-shell.tsx` is `"use client"`; keep new components server-rendered unless they need browser APIs or interactivity.

**Environment variables.** API reads `JOBFINDER_API_*` (with `DATABASE_URL`, `REDIS_URL`, `CORS_ALLOWED_ORIGINS` accepted as aliases). Web reads only `NEXT_PUBLIC_API_BASE_URL`. Never expose database URLs, Redis URLs, or other server secrets through `NEXT_PUBLIC_*`.

## Deployment

Two separate Vercel projects from this monorepo: `apps/api` (Python runtime, FastAPI entrypoint via `[project.scripts] app = "app.main:app"`) and `apps/web` (Next.js). Production URLs: `https://jobfinder.quentincasares.com` and `https://api.jobfinder.quentincasares.com`. Migrations are run **explicitly** before promoting an API deploy — do not put `alembic upgrade head` in the Vercel build command. Full runbook in `docs/vercel-deployment.md`.

## Editing Conventions Specific To This Repo

- Update tests **before** changing API behavior; the strict mypy + ruff + pytest gate will catch regressions cheaply.
- Keep changes scoped to the requested tranche. `docs/architecture.md` and `docs/decision-log.md` define what is intentionally deferred — do not "helpfully" add the deferred capability.
- When adding a service, follow the existing pattern: `__init__(self, session: Session, ...)`, raise typed domain exceptions, return Pydantic schemas (not ORM models). The route handler in `main.py` translates exceptions to HTTP.
- When modifying SQLAlchemy models, generate an Alembic migration in the same change. Do not edit existing migration files.
- After any UI change, verify the dashboard at `http://127.0.0.1:3000/` against a running API; the dashboard is the only user-visible surface, so behavior must be checked end-to-end, not just by tests.
- Pre-commit hooks (`.pre-commit-config.yaml`) duplicate the CI gate locally; install them with `pre-commit install` if not already.
