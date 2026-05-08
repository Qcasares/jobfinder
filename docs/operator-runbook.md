# Operator Runbook

Use local operator commands for production mutation endpoints. Do not put `JOBFINDER_API_OPERATOR_API_KEY` in browser code, public environment variables, screenshots, logs, or docs.

## Live Intake

Run a single approved HTTPS job page:

```bash
pnpm operator:live-intake -- --url https://careers.example.test/jobs/platform --source-domain careers.example.test
```

Run approved same-domain search discovery:

```bash
pnpm operator:live-intake -- --search --url https://careers.example.test/search?q=engineer --source-domain careers.example.test --max-results 10
```

The command reads `JOBFINDER_API_OPERATOR_API_KEY` from the shell or ignored file `apps/api/.env.operator.local`, sends it as `x-jobfinder-operator-key`, and prints the governed run result. Unknown sources are still denied before fetch.

If a live page presents CAPTCHA, bot-detection, login-only, identity-check, or access-control content, the run returns `manual_handoff_required` and includes `manual_handoff_id`. Review open handoffs through the API:

```bash
curl -fsS https://api.jobfinder.quentincasares.com/manual-handoffs
```

Create or resolve handoff records only from trusted operator tooling with `x-jobfinder-operator-key`. Do not paste the operator key into browser-visible code, screenshots, or documentation.

## Production Smoke

## Production Migrations

Run migrations from the API runtime when the production database URL is not available to local Alembic:

```bash
curl -fsS -X POST https://api.jobfinder.quentincasares.com/maintenance/migrations/upgrade \
  -H "x-jobfinder-operator-key: $JOBFINDER_API_OPERATOR_API_KEY"
```

This endpoint is production operator-key gated and runs Alembic only; it does not change source policy, candidate data, browser automation, or submission state.

## Production Smoke

Run the public smoke check after deployments and operator environment changes:

```bash
pnpm production:smoke
```

The smoke check does not read or print the operator key. It verifies that unauthenticated mutation attempts are rejected and that live capability gates are visible in runtime settings.
It also verifies that unauthenticated manual-handoff mutations are rejected in production.

## Guardrails

- Source policy must explicitly allow the action before live intake proceeds.
- CAPTCHA, bot detection, login walls, identity checks, and access controls are stop conditions.
- Manual-handoff records are metadata only and do not authorize bypass, autofill, credential use, or submission.
- Browser execution, real autofill, credential capture, and external submission remain blocked.
