# Jobfinder

Jobfinder is a governed job-search agent foundation. It keeps search intake, candidate material, drafting, autofill previews, and final-review packets behind explicit runtime flags and source-policy gates. The production posture remains review-first: no CAPTCHA bypass, bot-detection bypass, login automation, credential storage, real browser autofill, or external application submission is performed.

## Stack

- API: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, pytest, ruff, mypy, managed with `uv`.
- Web: Next.js App Router, React, TypeScript, Tailwind, managed with `pnpm`.
- API client: typed TypeScript fetch wrapper in `packages/api-client`.
- Local services: Postgres 16 and Redis through Docker Compose.

## Local Setup

```bash
cp .env.example .env
docker compose -f infra/compose.yaml up -d postgres redis
cd apps/api && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
cd ../.. && pnpm install && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm dev
```

Useful checks:

```bash
pnpm check
pnpm lint
pnpm typecheck
pnpm build
pnpm client:typecheck
pnpm client:test
pnpm api:lint
pnpm api:typecheck
pnpm api:openapi
pnpm api:openapi:write
pnpm api:test
```

The checked-in OpenAPI artifact is `docs/openapi/jobfinder-openapi.json`. Regenerate it with `pnpm api:openapi:write` after intentional API contract changes. The API health endpoint is `http://127.0.0.1:8000/health`. The web app defaults to `http://localhost:3000`.

## Deployment

Production dashboard: `https://jobfinder.quentincasares.com`.
Production API: `https://api.jobfinder.quentincasares.com`.

Use `docs/vercel-deployment.md` for the Vercel production runbook. Deploy the FastAPI API and Next.js web dashboard as separate Vercel projects from this monorepo, and run database migrations explicitly before promoting the API.

Use `docs/operator-runbook.md` for production live-intake commands. Operator keys stay in local ignored env files or Vercel secrets, never in browser-visible configuration.

## Guardrails

Unknown sources deny every action until reviewed. Audit events are append-only through the service layer and hash-chained for tamper evidence. Production mutation endpoints require an operator API key until a full auth provider exists. Live discovery is bounded to approved HTTPS sources, drafting requires evidence-backed review packets, autofill is dry-run preview data only, and final-review packets stop before external side effects. Use only synthetic fixtures and sanitized examples in this repository.
