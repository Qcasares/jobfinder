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

## Guardrails

- Source policy must explicitly allow the action before live intake proceeds.
- CAPTCHA, bot detection, login walls, identity checks, and access controls are stop conditions.
- Browser execution, real autofill, credential capture, and external submission remain blocked.
