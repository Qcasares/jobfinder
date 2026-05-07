# Live Discovery Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add operator-triggered live job extraction for explicitly approved sources while preserving deny-by-default policy, audit, and review gates.

**Architecture:** Add a synchronous `LiveDiscoveryService` that validates runtime flags and URL safety, checks `discover` and `extract` policies, fetches HTTPS content with strict limits, parses JSON-LD/static HTML into existing review item schemas, and records audit outcomes. Expose it through API endpoints and include live items in job/review reads without adding autofill, submit, browser automation, or LLM calls.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy, existing adapter/extraction services, `urllib.request` for bounded HTTP fetches, pytest.

---

## File Structure

- Create `apps/api/app/schemas/live_discovery.py`: request/response models and typed failure reasons.
- Create `apps/api/app/services/live_discovery.py`: policy-gated URL validation, fetch orchestration, parser selection, audit, and in-memory live run store.
- Modify `apps/api/app/config.py`: add live discovery runtime settings with safe defaults.
- Modify `apps/api/app/services/runtime_settings.py`: expose live discovery capability state.
- Modify `apps/api/app/schemas/review.py`: allow `data_origin="live_extraction"` and `synthetic=false`.
- Modify `apps/api/app/services/review_queue.py`: merge live review items into existing review queue output.
- Modify `apps/api/app/services/jobs.py`: consume the merged review queue through the existing path.
- Modify `apps/api/app/main.py`: add live discovery routes and inject the service into review/job endpoints.
- Modify `apps/api/tests/test_live_discovery.py`: cover policy denial, successful extraction, runtime disabled, URL rejection, and audit events.
- Modify `apps/api/tests/test_runtime_settings.py`: assert live discovery is off by default and explicit when enabled.

## Tasks

### Task 1: Schemas And Runtime Flags

**Files:**
- Create: `apps/api/app/schemas/live_discovery.py`
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/services/runtime_settings.py`
- Test: `apps/api/tests/test_runtime_settings.py`

- [x] Add `LiveDiscoveryRequest`, `LiveDiscoveryRun`, `LiveDiscoveryFailure`, and `LiveDiscoveryStatus` schemas.
- [x] Add `live_discovery_enabled`, `live_discovery_timeout_seconds`, and `live_discovery_max_bytes` settings.
- [x] Expose a `live_discovery` runtime capability that is disabled by default.
- [x] Run `cd apps/api && uv run pytest tests/test_runtime_settings.py -q`.

### Task 2: Policy-Gated Live Service

**Files:**
- Create: `apps/api/app/services/live_discovery.py`
- Test: `apps/api/tests/test_live_discovery.py`

- [x] Write tests for disabled runtime, unknown source denial before fetch, denied extract before fetch, and successful JSON-LD extraction from a fake fetcher.
- [x] Implement URL validation: HTTPS only, host required, normalized domain must match source policy domain after redirects.
- [x] Implement discover/extract checks through `SourceRegistryService` before fetch.
- [x] Implement audit events: `live_discovery.requested`, `live_discovery.denied`, `live_discovery.fetched`, `live_discovery.extracted`.
- [x] Run `cd apps/api && uv run pytest tests/test_live_discovery.py -q`.

### Task 3: API Surface And Queue Integration

**Files:**
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/schemas/review.py`
- Modify: `apps/api/app/services/review_queue.py`
- Modify: `apps/api/app/services/jobs.py`
- Test: `apps/api/tests/test_live_discovery.py`

- [x] Add `POST /live-discovery/runs` and `GET /live-discovery/runs/{run_id}`.
- [x] Add live run items to `ReviewQueueService` through a service-provided `raw_postings` argument.
- [x] Preserve existing synthetic fixture behavior when no live runs exist.
- [x] Confirm `synthetic=false` and `data_origin="live_extraction"` for live review items.
- [x] Run `cd apps/api && uv run pytest tests/test_live_discovery.py tests/test_review_queue.py tests/test_jobs.py -q`.

### Task 4: Contract And Full Verification

**Files:**
- Modify: `docs/openapi/jobfinder-openapi.json`
- Modify: `docs/source-policy.md`

- [x] Regenerate OpenAPI with `pnpm api:openapi:write`.
- [x] Document that live discovery requires explicit `discover` and `extract` approval and never enables autofill or submit.
- [x] Run `pnpm check`.

## Self Review

The plan covers the approved design: runtime flag, policy checks, URL/fetch limits, deterministic extraction, audit, review visibility, API surface, and verification. It intentionally excludes browser automation, autofill, submit, LLM calls, credential storage, and search-result crawling.
