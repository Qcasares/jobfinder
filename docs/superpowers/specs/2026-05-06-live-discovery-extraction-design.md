# Live Discovery And Extraction Design

## Purpose

Jobfinder can move from a synthetic-only foundation to a live intake tranche by adding live discovery and extraction for explicitly approved sources only. This phase does not add browser automation, autofill, LLM calls, or application submission. It satisfies the repository guardrails by making live network access opt-in, policy-gated, auditable, and review-first.

## Scope

In scope:

- Operator-triggered live extraction for a specific job URL.
- Source policy checks before any network request.
- Runtime kill switch for live discovery.
- HTTP fetch constraints: HTTPS only, timeout, byte limit, redirect/domain validation, and a Jobfinder user agent.
- Deterministic parsing through existing JSON-LD/static HTML adapters.
- Review queue and job catalog visibility for live extracted jobs.
- Hash-chained audit events for request, policy decision, fetch result, extraction result, and denial.

Out of scope for this tranche, but sequenced for later roadmap phases:

- Search-result crawling across job boards.
- Login-only pages.
- CAPTCHA, bot-detection, identity-check, or access-control detection and manual handoff.
- Browser automation, autofill, submit, or LLM-assisted drafting.
- Real candidate documents or third-party credential storage.

## Architecture

Add a `LiveDiscoveryService` in the API. It accepts a URL and source hint, normalizes the domain, evaluates `discover` and `extract` through `SourceRegistryService`, fetches only if both decisions allow the action, parses the response with deterministic adapters, and returns extracted review items. The first implementation runs synchronously inside the API request; Redis remains reserved for a later worker boundary.

The service keeps live data separate from synthetic fixtures by returning review items with `synthetic=false` and `data_origin="live_extraction"`. Existing dashboard/job APIs can combine synthetic fixture results with current live extraction results when available.

## Guardrails

Unknown sources deny by default. Prohibited, expired, login-only, CAPTCHA, non-HTTPS, oversized, timeout, and unsupported-content cases fail closed. All failures return typed responses and create audit records without attempting downstream extraction.

Policies must explicitly allow both `discover` and `extract` for a source before a fetch occurs. Allowing either action alone is insufficient. Autofill and submit remain denied and unimplemented.

CAPTCHA, bot-detection, identity-check, and access-control bypass are not future product goals. Later phases may detect these conditions, emit audit events, and route the operator to manual handoff.

## Testing

Tests must cover:

- Unknown source denies before fetch.
- Approved source fetches and extracts JSON-LD/static HTML.
- Approved source with denied extract does not fetch.
- Non-HTTPS and cross-domain redirect deny safely.
- Timeout/oversize/unsupported parser produces review-safe failure.
- Audit events are appended for live requests and outcomes.
- Runtime settings show live discovery as disabled by default and enabled only by explicit config.
