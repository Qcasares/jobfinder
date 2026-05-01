# Jobfinder

Jobfinder is a governed job-search agent foundation. The first tranche builds the audit, policy, API, and dashboard spine only. It does not crawl job boards, call LLMs, automate browsers, submit applications, or store real candidate data.

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

## Guardrails

Unknown sources deny every action until reviewed. Audit events are append-only through the service layer and hash-chained for tamper evidence. Use only synthetic fixtures and sanitized examples in this repository.
