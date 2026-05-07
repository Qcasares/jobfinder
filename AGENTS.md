# Repository Guidelines

## Project State

This repository is a governed Jobfinder foundation monorepo. It has a FastAPI API in `apps/api`, a Next.js dashboard in `apps/web`, a typed fetch client in `packages/api-client`, Docker Compose infrastructure in `infra`, synthetic fixtures, docs, CI, and pre-commit hooks.

## Product Guardrails

Keep the foundation deny-by-default and auditable. Unknown sources deny every action until reviewed. Audit events are append-only through the service layer and hash-chained. Use only synthetic fixtures and sanitized examples. Later-phase live capabilities must stay behind explicit runtime flags, source-policy gates, and review packets. Do not add CAPTCHA bypass, bot-detection bypass, login automation, third-party credential storage, real browser autofill, or external application submission without a separate approval-gated design.

## Commands

Run local services:

```bash
docker compose -f infra/compose.yaml up -d postgres redis
```

Run the API:

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run the web app:

```bash
pnpm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm dev
```

## Verification

Use `pnpm check` for the full local gate. It covers web lint/type/test/build, API client type/test, API lint/type/test. For migration state, run:

```bash
cd apps/api
uv run alembic current
```

Before reporting completion, verify the relevant browser surface at `http://127.0.0.1:3000/` when UI behavior changed.

## Editing Notes

Prefer repo patterns over new abstractions. Keep changes scoped to the requested tranche. Update tests before implementation for new behavior. Keep secrets, generated documents, screenshots, browser traces, and real candidate data out of the repository.
