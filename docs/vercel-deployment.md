# Vercel Deployment Runbook

Jobfinder should deploy to Vercel as two projects from the same GitHub repository. Keep the API and web dashboard separate so the frontend can be promoted independently from the FastAPI service and database migrations.

## Project Shape

Current production URLs:

- Web: `https://jobfinder.quentincasares.com`
- API: `https://api.jobfinder.quentincasares.com`
- Fallback web alias: `https://jobfinder-qcasares-projects.vercel.app`
- Fallback API alias: `https://jobfinder-api-qcasares-projects.vercel.app`

### API Project

- Root Directory: `apps/api`
- Framework Preset: FastAPI or Other
- Runtime: Vercel Python runtime
- FastAPI entrypoint: `[project.scripts] app = "app.main:app"` in `apps/api/pyproject.toml`
- Production URL: `https://api.jobfinder.quentincasares.com`

Required production environment variables:

```text
JOBFINDER_API_ENVIRONMENT=production
JOBFINDER_API_WRITE_API_ENABLED=false
JOBFINDER_API_OPERATOR_API_KEY=<strong-random-operator-secret>
JOBFINDER_API_LIVE_DISCOVERY_ENABLED=false
JOBFINDER_API_LIVE_SEARCH_DISCOVERY_ENABLED=false
JOBFINDER_API_LIVE_DISCOVERY_TIMEOUT_SECONDS=8
JOBFINDER_API_LIVE_DISCOVERY_MAX_BYTES=1000000
JOBFINDER_API_CANDIDATE_VAULT_ENABLED=false
JOBFINDER_API_LLM_DRAFTING_ENABLED=false
JOBFINDER_API_AUTOFILL_PACKETS_ENABLED=false
JOBFINDER_API_SUBMISSION_PACKETS_ENABLED=false
JOBFINDER_API_DATABASE_URL=<managed-postgres-sqlalchemy-url>
JOBFINDER_API_REDIS_URL=
JOBFINDER_API_CORS_ALLOWED_ORIGINS=["https://jobfinder.quentincasares.com","https://jobfinder-qcasares-projects.vercel.app"]
```

Do not deploy the API without a managed Postgres database. The local default database URL points at Docker Compose and is not valid in Vercel. Redis is included for future readiness but no queue worker depends on it in this tranche.

Production write endpoints are disabled by default because this phase has no auth provider. Keep `JOBFINDER_API_WRITE_API_ENABLED=false` until authentication, roles, and operator controls exist. Production mutation endpoints also require `x-jobfinder-operator-key` to match `JOBFINDER_API_OPERATOR_API_KEY`; do not enable live capability flags unless that secret is configured. Keep the live capability flags disabled unless the environment has the matching approval workflow, source policies, and operator controls configured; each flag unlocks only its governed API surface and still stops before external submission.

Run database migrations against the production database before promoting traffic:

```bash
cd apps/api
JOBFINDER_API_DATABASE_URL=<managed-postgres-sqlalchemy-url> uv run alembic upgrade head
```

Do not run migrations automatically in the Vercel build command. Builds can run for previews and retries; migrations should remain an explicit release step until a safer migration workflow exists.

### Web Project

- Root Directory: `apps/web`
- Framework Preset: Next.js
- Package manager: pnpm
- Build Command: `pnpm build`
- Production URL: `https://jobfinder.quentincasares.com`

Required production environment variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://api.jobfinder.quentincasares.com
```

The dashboard page is marked dynamic so Vercel renders it per request and reads the current API/fallback state instead of freezing build-time data.

## Deployment Order

1. Create or connect the API project in Vercel with root directory `apps/api`.
2. Attach a managed Postgres database and set `JOBFINDER_API_DATABASE_URL`.
3. Set `JOBFINDER_API_CORS_ALLOWED_ORIGINS` to the final web production origin.
4. Run `uv run alembic upgrade head` against the managed database.
5. Deploy the API and verify `/health` and `/settings/runtime`.
6. Create or connect the web project in Vercel with root directory `apps/web`.
7. Set `NEXT_PUBLIC_API_BASE_URL` to the API production URL.
8. Deploy the web project and verify the dashboard shows `API data` and the current live capability states.

## Preflight Checks

Run these locally before pushing a production deployment commit:

```bash
pnpm check
cd apps/api && uv run alembic current
curl -fsS http://127.0.0.1:8000/health
curl -fsSI http://127.0.0.1:3000/
```

## Guardrails

- Only governed live surfaces should be deployed: bounded approved-source discovery, metadata-only candidate document records, evidence-backed draft packets, dry-run autofill packets, and final-review packets.
- Keep production mutation endpoints behind the operator API key until a full auth provider replaces it.
- Do not add CAPTCHA bypass, bot-detection bypass, login automation, third-party credential storage, real browser autofill, or external application submission without a separate approval-gated design.
- Keep real candidate data out of fixtures, docs, and seed data.
- Keep `NEXT_PUBLIC_API_BASE_URL` as the only client-exposed API setting.
- Do not expose database URLs, Redis URLs, API keys, or other secrets in the web project.
