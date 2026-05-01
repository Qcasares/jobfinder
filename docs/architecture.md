# Architecture

Jobfinder is planned as a governed job-search assistant, not a blind auto-apply crawler. The phase 0/1 foundation establishes the project boundaries, local infrastructure, typed contracts, persistence model, audit trail, and dashboard shell needed before any live discovery or agent automation is introduced. Phase 2 adds the source registry and policy engine boundary so source actions can be evaluated before future discovery, extraction, drafting, autofill, or submission workflows are built.

## Phase 0/1 Foundation

The MVP foundation is split across:

- `apps/api`: FastAPI backend with Pydantic v2 request/response models, SQLAlchemy persistence, Alembic migrations, health checks, and deterministic helpers.
- `apps/web`: Next.js dashboard shell for reviewing system state and future approval queues.
- `infra`: local Postgres and Redis dependencies through Docker Compose, plus future migration and deployment support.
- `docs`: architecture, operating decisions, and implementation notes.
- `fixtures`: synthetic or sanitized adapter and schema examples for deterministic tests.
- `packages/api-client`: future generated TypeScript client from the backend OpenAPI schema.

Postgres is the system of record for candidate evidence, source policies, extracted jobs, scoring decisions, application state, approvals, and audit events. Redis is included in local infrastructure so queue/cache integration can be added without changing the developer dependency shape, but it should remain unused until a worker or background job boundary exists.

The API should expose typed OpenAPI contracts generated from Pydantic models. The web dashboard and future TypeScript client should consume those contracts rather than maintaining hand-written duplicate schemas.

## Governance Model

All material workflow transitions must be auditable. Source policy checks, extraction provenance, score rationale, generated claims, form answers, approvals, and submissions should produce append-only audit events. Generated application materials must map claims back to approved candidate evidence.

Source policy is deny-by-default. A source must explicitly allow the intended action before the system can discover, extract, draft, autofill, or submit. Ambiguous or prohibited platforms are routed to manual review.

The phase 2 source registry records allowed, denied, and review-required actions per source, along with policy evidence references, review timestamps, and rationale. LinkedIn and Indeed remain known prohibited examples in the default policy posture. Robots cache data supports repeatable policy decisions for approved sources, but it is not a permission grant.

## Explicit Deferrals

Phase 0/1 does not include live crawling, browser automation, LLM calls, ATS adapters, autonomous submissions, CAPTCHA handling, production deployment, multi-user authentication, or real candidate data storage. Phase 2 source registry and policy work also defers crawling, adapters, LLM calls, browser automation, autofill, and submissions; it only defines and records the policy decisions those later capabilities must obey.
