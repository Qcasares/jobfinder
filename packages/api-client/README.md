# @jobfinder/api-client

Typed fetch client for the governed Jobfinder API foundation.

The current client is intentionally narrow. It exposes helpers for existing safe endpoints:

- `getHealth()`
- `getRuntimeSettings()`
- `checkSourcePolicy()`

It does not expose helpers for crawling, LLM calls, browser automation, autofill, or application submission. When OpenAPI generation is wired later, FastAPI/Pydantic should remain the source of truth and this package should keep the same safety boundary.

Run package checks from the repo root:

```sh
pnpm --filter @jobfinder/api-client typecheck
pnpm --filter @jobfinder/api-client test
```
