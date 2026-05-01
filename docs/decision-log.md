# Decision Log

This log records early foundation decisions for Jobfinder. Decisions may be revisited, but changes should be explicit and auditable.

## SQLAlchemy Over SQLModel

Use SQLAlchemy for persistence models. SQLAlchemy gives direct control over relationships, constraints, indexes, migrations, and database-specific behavior. Pydantic remains responsible for API and validation schemas instead of coupling persistence and transport concerns through SQLModel.

## Pydantic/OpenAPI As Source Of Truth

Use Pydantic v2 schemas to define request, response, and agent output contracts. FastAPI's generated OpenAPI document is the source of truth for external clients. The future TypeScript API client should be generated from OpenAPI rather than maintained by hand.

## Deny-By-Default Source Policy

Source automation permissions are denied unless explicitly allowed. Policies should distinguish discovery, extraction, drafting, autofill, and submission. Ambiguous policies, prohibited platforms, CAPTCHA, bot detection, login controls, or identity checks must route to manual handoff.

## Phase 2 Source Registry Boundary

Implement source registry and policy engine work before any live crawler, adapter, LLM, browser automation, autofill, or submission feature. Registry entries should store source identity, action-level policy posture, evidence references, review metadata, and rationale. LinkedIn and Indeed remain default prohibited examples for automated job-search actions unless future written authorization is reviewed and recorded.

## Hash-Chained Audit

Use append-only audit events with hash chaining so material decisions can be verified after the fact. Audit entries should cover policy checks, extraction provenance, score rationale, generated claims, form answers, approvals, and submissions.

## Single-User Local Auth Model

Start with a single-user local model for phase 0/1. This keeps the foundation focused on governed workflow correctness before multi-user account management, organizations, roles, or production identity providers are introduced.

## Redis Included For Future Readiness Only

Include Redis in local infrastructure for future queues, background jobs, rate limits, and cache boundaries. Do not require Redis for synchronous phase 0/1 behavior until a concrete worker or orchestration path depends on it.
