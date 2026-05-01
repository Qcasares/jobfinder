# governed job-search agent — Codex development plan

## 1. product objective

Build a governed job-search agent and application orchestration platform that discovers suitable jobs, extracts structured job data, scores role fit, drafts factually accurate tailored application materials, supports assisted application workflows, and performs autonomous submission only for allowlisted sources where automation is permitted and risk is low.

The product should optimise for quality, fit, explainability, and compliant execution rather than high-volume mass application. Think of it as “Moneyball for job applications”: fewer shots, better expected value, tighter feedback loops.

## 2. strategic product position

Do **not** begin with a blind auto-apply crawler. The stronger product is a governed agentic workflow with these differentiators:

- API-first job discovery before scraping.
- Evidence-backed CV/resume tailoring.
- Source policy registry for terms, robots, rate limits, and allowed actions.
- Human-in-the-loop gates for sensitive actions.
- Browser automation only as a controlled fallback.
- Full audit trail for every extraction, score, generated claim, form answer, and submission.
- Outcome analytics to learn which sources, CV variants, and criteria produce interviews.

## 3. research-backed constraints and design implications

### 3.1 terms and platform restrictions

Some major platforms prohibit automated application activity. Indeed’s current legal terms prohibit automation, scripting, or bots to automate the Indeed Apply process outside official tooling. LinkedIn also restricts scraping and automated activity through third-party tools. Therefore, the system must not treat all websites as automatable targets.

Design implication:

- Add a source policy registry.
- Separate `discover`, `extract`, `draft`, `autofill`, and `submit` permissions.
- Never bypass CAPTCHA, bot detection, login controls, paywalls, or identity checks.
- Route prohibited or ambiguous sources to manual handoff.

### 3.2 API-first discovery

ATS platforms and aggregators increasingly expose job-posting APIs. Practical targets include Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Personio, and unified/aggregator APIs. Aggregators can provide breadth but usually trade off control, price, and dependency risk.

Design implication:

Source priority order:

1. Official ATS or job-board API.
2. Licensed aggregator API.
3. Structured `JobPosting` data from JSON-LD or microdata.
4. Sitemap/RSS/feed extraction.
5. Static HTML parsing.
6. Browser-rendered extraction.
7. Manual review.

### 3.3 structured data first

Schema.org and Google support `JobPosting` structured data with fields for title, hiring organisation, location, salary, employment type, remote information, valid-through date, and related attributes.

Design implication:

- Build a structured-data extractor before LLM extraction.
- Use LLMs for ambiguous, incomplete, or unstructured pages.
- Store extraction confidence and provenance for every field.

### 3.4 agent orchestration maturity

For production agents, prefer explicit workflows, state checkpoints, typed outputs, and human approval gates over free-running autonomous loops. LangGraph is strong for durable stateful workflows and human-in-the-loop pauses. OpenAI Agents SDK is strong for model orchestration, handoffs, guardrails, tracing, and tool use. Pydantic AI is strong for typed structured outputs and clean Python ergonomics.

Design implication:

- Use a graph workflow as the system backbone.
- Use specialist agents as nodes, not as unconstrained peers.
- Persist state after every material decision.
- Validate every agent output with Pydantic models.

### 3.5 browser automation maturity

Browser automation remains useful but brittle and policy-sensitive. Stagehand combines Playwright-style deterministic browser control with AI-powered `observe`, `extract`, and `act` patterns. Browser-use is Python-first and more autonomous; Stagehand is TypeScript-first and better suited to deterministic, auditable browser flows.

Design implication:

- Use browser automation for controlled assisted workflows and allowlisted autonomous flows.
- Use deterministic selectors and Playwright scripts wherever possible.
- Use AI browser actions only for resilient observation or ambiguous UI steps.
- Capture screenshots, DOM snapshots, form schema, and action logs.

## 4. recommended technology stack

### 4.1 stack summary

Recommended default stack:

- **Frontend:** Next.js, React, TypeScript, Tailwind, shadcn/ui.
- **Backend API:** Python FastAPI.
- **Agent/workflow runtime:** LangGraph for durable graph orchestration.
- **Agent SDK layer:** OpenAI Agents SDK for specialist agents, tool calls, tracing, guardrails, and handoffs where useful.
- **Structured output validation:** Pydantic v2 / Pydantic AI patterns.
- **Browser automation:** Playwright plus Stagehand; Browserbase optional for hosted browser sessions.
- **Job data ingestion:** Adapter framework with official ATS APIs first; optional aggregator integration later.
- **Database:** PostgreSQL with pgvector.
- **Cache/queue:** Redis plus Celery, Dramatiq, or Temporal.
- **Search/indexing:** Postgres full-text for MVP; OpenSearch or Meilisearch later.
- **Object storage:** S3-compatible storage for CVs, screenshots, generated documents, and audit artefacts.
- **Document generation:** docxtpl/python-docx for `.docx`; WeasyPrint or Playwright PDF for PDFs; Markdown as canonical intermediate.
- **Observability:** OpenTelemetry, structured logs, LangSmith or equivalent for LangGraph traces, OpenAI tracing for agent runs, Sentry for application errors.
- **Secrets:** Vault, Doppler, AWS Secrets Manager, Azure Key Vault, or environment-managed secrets.
- **Deployment:** Docker Compose for local; Kubernetes, Fly.io, Render, Railway, or AWS ECS for production; GitHub Actions for CI/CD.

### 4.2 why this stack

#### Python backend over Node backend

Python is better for this product’s core: NLP, LLM orchestration, extraction pipelines, scoring, document processing, embeddings, and data science. A TypeScript frontend remains ideal for the user-facing dashboard and browser-automation bridge.

#### LangGraph over free-form multi-agent frameworks

This product needs checkpoints, retries, auditability, and approval gates. A graph is the right abstraction because the workflow has clear stages: discover, extract, score, tailor, validate, apply, track. Agents should act like specialist players in a drilled team, not like eleven strikers chasing the same ball.

#### Stagehand plus Playwright over pure autonomous browser agents

Autonomous browser agents are impressive but fragile. Job applications require precision, auditability, and reversibility. Playwright gives deterministic control; Stagehand adds resilience where selectors break or UI is unfamiliar.

#### Postgres plus pgvector over a separate vector database at MVP

Postgres handles relational records, audit trails, criteria, applications, and deduplication. pgvector is enough for semantic matching during MVP. Move to a dedicated vector database only when scale or retrieval complexity demands it.

#### OpenAI Agents SDK plus Pydantic outputs

Use the Agents SDK where handoffs, guardrails, and tracing add value. Use Pydantic models for every structured agent output so Codex can write tests against schemas rather than prose.

## 5. target architecture

```text
+---------------------------+
| Next.js dashboard          |
| - criteria setup           |
| - review queue             |
| - CV diff viewer           |
| - application tracker      |
+-------------+-------------+
              |
              v
+---------------------------+
| FastAPI backend            |
| - auth                     |
| - user profile API         |
| - job API                  |
| - application API          |
| - policy API               |
+-------------+-------------+
              |
              v
+---------------------------+       +---------------------------+
| LangGraph workflow engine  |<----->| agent/tool layer           |
| - durable state            |       | - discovery agent          |
| - approval gates           |       | - extraction agent         |
| - retries/checkpoints      |       | - scoring agent            |
| - audit transitions        |       | - tailoring agent          |
+-------------+-------------+       | - form agent               |
              |                     | - compliance agent         |
              v                     +---------------------------+
+---------------------------+
| adapters and tools         |
| - ATS API adapters         |
| - aggregator adapters      |
| - JSON-LD extractor        |
| - HTML extractor           |
| - Playwright/Stagehand     |
| - document generator       |
+-------------+-------------+
              |
              v
+---------------------------+
| data layer                 |
| - PostgreSQL               |
| - pgvector                 |
| - Redis queue/cache        |
| - object storage           |
| - audit/event log          |
+---------------------------+
```

## 6. agent and skill design

### 6.1 agents

Implement agents as bounded specialists with typed inputs and outputs. Avoid one general “do everything” agent.

#### 1. source intelligence agent

Purpose:

- identify source type;
- detect ATS platform;
- inspect robots and visible policy signals;
- recommend access method;
- update source policy registry draft.

Output model:

```python
class SourceAssessment(BaseModel):
    domain: str
    source_type: Literal["ats", "job_board", "company_careers", "recruiter", "aggregator", "unknown"]
    detected_platform: str | None
    recommended_access_method: Literal["api", "aggregator", "json_ld", "html", "browser", "manual"]
    allowed_actions: list[Literal["discover", "extract", "draft", "autofill", "submit"]]
    prohibited_actions: list[str]
    confidence: float
    evidence_urls: list[str]
    notes: str
```

#### 2. discovery agent

Purpose:

- query configured sources;
- call source adapters;
- discover job URLs;
- create raw job records;
- avoid duplicate crawling.

This should mostly be deterministic code. Use an LLM only for source classification or ambiguous source interpretation.

#### 3. extraction agent

Purpose:

- extract canonical job fields;
- prefer structured data;
- use LLM fallback;
- produce field-level provenance and confidence.

Output model:

```python
class ExtractedJobPosting(BaseModel):
    source_url: str
    application_url: str | None
    title: str
    company: str
    locations: list[str]
    remote_type: Literal["remote", "hybrid", "onsite", "unknown"]
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    employment_type: str | None
    seniority: str | None
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    qualifications: list[str]
    posted_date: date | None
    valid_through: date | None
    extraction_confidence: float
    field_provenance: dict[str, str]
```

#### 4. fit scoring agent

Purpose:

- compare job against user criteria and evidence bank;
- produce transparent scoring;
- classify role as apply, review, monitor, or reject.

Score dimensions:

- title fit;
- skills fit;
- seniority fit;
- salary fit;
- location fit;
- sector/company fit;
- work-pattern fit;
- evidence strength;
- risk/friction score;
- freshness score.

#### 5. CV tailoring agent

Purpose:

- tailor CV/resume without inventing facts;
- map every claim to evidence IDs;
- generate CV diff;
- optimise for ATS readability.

Hard rule:

- No generated sentence may introduce an unsupported factual claim.

Output model:

```python
class TailoredDocument(BaseModel):
    job_id: str
    candidate_profile_id: str
    document_type: Literal["cv", "resume", "cover_letter", "supporting_statement"]
    markdown_content: str
    claim_evidence_map: dict[str, list[str]]
    unsupported_claims: list[str]
    ats_readability_score: float
    keyword_alignment_score: float
    factual_support_score: float
    diff_summary: list[str]
```

#### 6. form understanding agent

Purpose:

- inspect application form;
- classify fields;
- map fields to candidate profile data;
- identify sensitive or ambiguous questions;
- decide whether to continue, pause, or abort.

Question risk classes:

- low: name, email, phone, location, links;
- medium: salary expectations, notice period, work pattern;
- high: work authorisation, criminal record, diversity, disability, medical, background checks, non-compete, conflicts;
- blocking: CAPTCHA, identity verification, legal attestation without prepared answer, unsupported required claim.

#### 7. application execution agent

Purpose:

- complete allowlisted forms using deterministic automation;
- pause before final submission unless autonomous mode criteria are satisfied;
- record every field and submitted value;
- store confirmation ID and screenshot.

#### 8. outcome learning agent

Purpose:

- ingest application outcomes;
- cluster rejection reasons;
- compare CV variants;
- refine search criteria suggestions;
- flag weak sources or ghost jobs.

### 6.2 skills

In addition to agents, implement deterministic skills/tools. These should be callable by the graph and independently unit-tested.

Core skills:

- `detect_ats_platform(url_or_html)`
- `fetch_robots_policy(domain)`
- `extract_json_ld_jobposting(html)`
- `extract_open_graph(html)`
- `normalise_salary(text, locale)`
- `normalise_location(text)`
- `dedupe_job_postings(job_a, job_b)`
- `score_job_fit(job, criteria, evidence_bank)`
- `retrieve_candidate_evidence(job_requirements)`
- `generate_tailored_cv(job, evidence)`
- `validate_claims_against_evidence(document, evidence_bank)`
- `validate_ats_readability(document)`
- `classify_form_question(question)`
- `fill_application_form(form_schema, answers)`
- `generate_manual_handoff_packet(job, documents, missing_answers)`
- `track_application_status(application_id)`

## 7. data model

### 7.1 core tables

Minimum tables:

- `users`
- `candidate_profiles`
- `candidate_evidence`
- `search_criteria`
- `sources`
- `source_policies`
- `source_policy_evidence`
- `crawl_runs`
- `raw_job_pages`
- `job_postings`
- `job_posting_embeddings`
- `job_scores`
- `generated_documents`
- `document_claims`
- `document_claim_evidence`
- `application_forms`
- `application_form_fields`
- `application_answers`
- `applications`
- `application_events`
- `approval_requests`
- `audit_events`
- `outcomes`

### 7.2 source policy registry

Fields:

```sql
CREATE TABLE source_policies (
    id UUID PRIMARY KEY,
    domain TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    detected_platform TEXT,
    access_method TEXT NOT NULL,
    robots_status TEXT,
    terms_status TEXT,
    can_discover BOOLEAN NOT NULL DEFAULT FALSE,
    can_extract BOOLEAN NOT NULL DEFAULT FALSE,
    can_draft BOOLEAN NOT NULL DEFAULT TRUE,
    can_autofill BOOLEAN NOT NULL DEFAULT FALSE,
    can_submit BOOLEAN NOT NULL DEFAULT FALSE,
    requires_auth BOOLEAN NOT NULL DEFAULT FALSE,
    rate_limit_per_hour INTEGER,
    policy_confidence NUMERIC NOT NULL DEFAULT 0,
    last_reviewed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 7.3 candidate evidence bank

Fields:

```sql
CREATE TABLE candidate_evidence (
    id UUID PRIMARY KEY,
    candidate_profile_id UUID NOT NULL REFERENCES candidate_profiles(id),
    evidence_type TEXT NOT NULL,
    title TEXT NOT NULL,
    organisation TEXT,
    start_date DATE,
    end_date DATE,
    description TEXT NOT NULL,
    metrics JSONB,
    skills TEXT[],
    source_document_id UUID,
    confidence NUMERIC NOT NULL DEFAULT 1.0,
    permitted_wording TEXT[],
    forbidden_wording TEXT[],
    verification_status TEXT NOT NULL DEFAULT 'user_supplied',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 7.4 application audit event

Every material action must write an audit event.

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_name TEXT,
    input_hash TEXT,
    output_hash TEXT,
    decision TEXT,
    rationale TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 8. workflow design

### 8.1 discovery workflow

1. Load active search criteria.
2. Load enabled sources.
3. For each source, check policy registry.
4. Select highest-permission access method.
5. Run source adapter.
6. Store raw job records.
7. Deduplicate by canonical URL, company, title, location, and semantic similarity.
8. Queue extraction.

### 8.2 extraction workflow

1. Try official API fields.
2. Try JSON-LD / microdata.
3. Try static HTML extraction.
4. Use LLM extraction if confidence is low.
5. Validate required fields.
6. Store field-level provenance.
7. Queue scoring.

### 8.3 scoring workflow

1. Compare job to criteria.
2. Retrieve relevant candidate evidence.
3. Calculate deterministic scores.
4. Ask scoring agent to produce rationale and flags.
5. Classify outcome:
   - reject;
   - monitor;
   - review;
   - draft application;
   - auto-apply candidate.
6. Store score and rationale.

### 8.4 tailoring workflow

1. Retrieve master CV and evidence bank.
2. Select relevant evidence.
3. Generate tailored markdown CV.
4. Generate cover letter/supporting statement if required.
5. Validate every factual claim.
6. Run ATS-readability checks.
7. Produce diff versus master/default CV.
8. Create approval request unless user policy allows auto-proceed.

### 8.5 application workflow

1. Check source policy.
2. Open application URL in controlled browser session if allowed.
3. Extract form schema.
4. Classify fields by risk.
5. Auto-fill low-risk fields.
6. Use user-approved rules for medium-risk fields.
7. Pause on high-risk or blocking fields.
8. Upload generated CV and documents.
9. Pause before final submit unless autonomous criteria are satisfied.
10. Submit only if policy, confidence, and user mode allow it.
11. Store confirmation artefacts.
12. Update tracker.

### 8.6 manual handoff workflow

For prohibited or uncertain sources, generate a handoff packet:

- job summary;
- match rationale;
- application URL;
- tailored CV;
- cover letter/supporting statement;
- field answers that can be safely copied;
- unanswered sensitive questions;
- source policy reason for not automating.

## 9. operating modes

Implement these modes as user-level and source-level policies.

| Mode | Discovery | Tailoring | Form filling | Submission |
|---|---:|---:|---:|---:|
| Monitor only | Yes | No | No | No |
| Draft only | Yes | Yes | No | No |
| Assisted apply | Yes | Yes | Yes | User submits |
| Governed auto-apply | Yes | Yes | Yes | System submits only when all gates pass |

## 10. approval gates

The workflow must support gates at:

1. Source policy approval.
2. Extraction confidence threshold.
3. Match score threshold.
4. CV factual validation.
5. ATS readability validation.
6. Sensitive question classification.
7. Final submission.

Each gate records:

- machine decision;
- confidence;
- rationale;
- artefacts;
- human approval/override;
- timestamp.

## 11. MVP scope

### 11.1 MVP product goal

Create an assisted-apply product that discovers roles, scores them, drafts tailored applications, and generates a manual or semi-automated application packet. Full autonomous submission should be behind feature flags and limited to allowlisted low-risk test sources.

### 11.2 MVP source adapters

Build these first:

1. Greenhouse job board adapter.
2. Lever postings adapter.
3. Ashby public postings adapter.
4. Workable published jobs adapter.
5. SmartRecruiters postings adapter.
6. Generic `JobPosting` JSON-LD adapter.
7. Generic static HTML adapter.

Defer:

- LinkedIn automation;
- Indeed Apply automation;
- CAPTCHA handling;
- Workday auto-submit;
- recruiter email automation;
- private/authenticated scraping.

### 11.3 MVP features

- User profile and master CV upload.
- Evidence bank extraction from master CV.
- Search criteria setup.
- Source registry.
- API/structured-data discovery.
- Job extraction and deduplication.
- Fit scoring.
- Tailored CV markdown and `.docx` generation.
- Cover letter generation.
- Claim-to-evidence validation.
- ATS readability checks.
- Review queue.
- Manual handoff packet.
- Application tracker.
- Audit events.

## 12. implementation phases for Codex

### phase 0 — repository and architecture setup

Tasks:

- Create monorepo structure:
  - `apps/web`
  - `apps/api`
  - `packages/shared-schemas`
  - `workers`
  - `infra`
  - `docs`
- Add Docker Compose for Postgres, Redis, API, web, and worker.
- Add `.env.example`.
- Add GitHub Actions for lint, tests, type checks, and migrations.
- Add pre-commit hooks.

Acceptance criteria:

- `docker compose up` starts local stack.
- API health endpoint returns OK.
- Web app loads dashboard shell.
- CI passes.

### phase 1 — database and schema

Tasks:

- Create Alembic migrations.
- Implement SQLAlchemy models or SQLModel models.
- Add Pydantic API schemas.
- Add seed data for source policies and sample candidate.
- Add audit event helper.

Acceptance criteria:

- Migrations run from clean database.
- Unit tests validate core model constraints.
- Audit helper writes immutable events.

### phase 2 — source registry and policy engine

Tasks:

- Implement `SourcePolicyService`.
- Implement robots fetch/cache.
- Implement domain normalisation.
- Implement allowed-action checks.
- Add admin UI for source policies.
- Seed known policies for LinkedIn and Indeed as manual/no-submit unless official integration exists.

Acceptance criteria:

- Policy check blocks prohibited actions.
- Every blocked action returns an explainable reason.
- Policy decisions are audit-logged.

### phase 3 — job source adapters

Tasks:

- Define `JobSourceAdapter` interface.
- Implement Greenhouse adapter.
- Implement Lever adapter.
- Implement Ashby adapter.
- Implement SmartRecruiters adapter.
- Implement Workable adapter.
- Implement JSON-LD adapter.
- Implement static HTML adapter.
- Add adapter tests with recorded fixtures.

Acceptance criteria:

- Each adapter emits canonical `RawJobPosting` records.
- Fixtures cover missing salary, multiple locations, remote jobs, and expired jobs.
- Deduplication prevents duplicates across sources.

### phase 4 — extraction and normalisation

Tasks:

- Implement structured extraction pipeline.
- Add salary parser.
- Add location parser.
- Add remote/hybrid classifier.
- Add skill extraction with deterministic and LLM fallback.
- Store field-level provenance.

Acceptance criteria:

- Extraction returns valid `ExtractedJobPosting` schema.
- Each field has source/provenance.
- Low-confidence extraction is routed to review.

### phase 5 — fit scoring engine

Tasks:

- Implement deterministic scoring weights.
- Add configurable weights per user.
- Add semantic skill matching with embeddings.
- Add transparent rationale generation.
- Add reject/review/apply thresholds.

Acceptance criteria:

- Given sample jobs and criteria, scoring is deterministic.
- Rationale explains top positive and negative factors.
- Scores are stored and visible in UI.

### phase 6 — evidence bank

Tasks:

- Parse master CV into evidence candidates.
- Let user edit/approve evidence items.
- Add evidence embeddings.
- Add evidence retrieval by job requirements.
- Add evidence confidence and verification status.

Acceptance criteria:

- User can review and edit evidence bank.
- Evidence retrieval returns relevant facts for target job.
- Tailoring cannot use unapproved evidence unless explicitly allowed.

### phase 7 — CV and cover-letter tailoring

Tasks:

- Create markdown canonical document format.
- Implement CV tailoring agent.
- Implement claim extraction.
- Implement claim-to-evidence validator.
- Implement unsupported-claim blocker.
- Implement `.docx` generation.
- Implement PDF generation if needed.
- Add CV diff viewer.

Acceptance criteria:

- Every factual claim maps to evidence IDs.
- Unsupported claims block finalisation.
- User can view diff against baseline CV.
- Generated `.docx` opens correctly.

### phase 8 — ATS readability and keyword alignment

Tasks:

- Implement ATS format checks.
- Implement keyword coverage report.
- Add missing-keyword suggestions based only on supported evidence.
- Add file compatibility checks.

Acceptance criteria:

- System returns ATS readability score.
- System distinguishes keyword gaps from unsupported claims.
- Suggestions never invent skills or credentials.

### phase 9 — review queue and manual handoff

Tasks:

- Build review queue UI.
- Add filters by score, salary, location, source, and status.
- Add generated application packet view.
- Add approve/reject/edit actions.
- Generate manual handoff packet.

Acceptance criteria:

- User can complete a manual application using generated packet.
- Every approval or rejection is audit-logged.
- Manual source restrictions are clearly explained.

### phase 10 — controlled browser automation

Tasks:

- Add Playwright service.
- Add Stagehand integration for observe/extract/act where deterministic selectors are insufficient.
- Create browser session logging.
- Extract form schema from allowlisted test pages.
- Classify form fields.
- Fill low-risk fields.
- Pause before final submit.

Acceptance criteria:

- Browser automation works on a local test ATS form.
- Screenshots and DOM snapshots are stored.
- High-risk fields trigger approval gate.
- Final submit requires approval by default.

### phase 11 — governed autonomous submission

Tasks:

- Add feature flag for autonomous submission.
- Restrict to allowlisted domains and low-risk forms.
- Enforce source policy, confidence, and approval gates.
- Store confirmation artefacts.

Acceptance criteria:

- Auto-submit cannot run on denylisted domains.
- Auto-submit cannot answer high-risk questions without explicit stored rule.
- Confirmation IDs/screenshots are stored.

### phase 12 — outcome analytics

Tasks:

- Add statuses: discovered, drafted, reviewed, applied, rejected, interview, offer, archived.
- Add response-rate analytics.
- Add source effectiveness analytics.
- Add CV variant analytics.
- Add rejection reason clustering.

Acceptance criteria:

- Dashboard shows funnel metrics.
- User can compare outcomes by source and CV variant.
- Analytics do not update scoring weights automatically without user approval.

## 13. API endpoints

Suggested FastAPI routes:

```text
GET    /health
POST   /candidate-profiles
GET    /candidate-profiles/{id}
POST   /candidate-profiles/{id}/evidence/import
GET    /candidate-profiles/{id}/evidence
PATCH  /candidate-evidence/{id}

POST   /search-criteria
GET    /search-criteria
PATCH  /search-criteria/{id}

GET    /sources
POST   /sources
GET    /source-policies
PATCH  /source-policies/{id}
POST   /source-policies/{id}/review

POST   /crawl-runs
GET    /crawl-runs/{id}
GET    /jobs
GET    /jobs/{id}
POST   /jobs/{id}/score
POST   /jobs/{id}/draft-application

GET    /generated-documents/{id}
POST   /generated-documents/{id}/validate
POST   /generated-documents/{id}/export/docx
POST   /generated-documents/{id}/export/pdf

GET    /review-queue
POST   /approval-requests/{id}/approve
POST   /approval-requests/{id}/reject

POST   /applications/{job_id}/handoff-packet
POST   /applications/{job_id}/assisted-apply
POST   /applications/{job_id}/submit
GET    /applications
GET    /applications/{id}
PATCH  /applications/{id}/status

GET    /analytics/funnel
GET    /analytics/sources
GET    /analytics/cv-variants
```

## 14. frontend screens

Build screens in this order:

1. Dashboard overview.
2. Candidate profile and evidence bank.
3. Search criteria editor.
4. Source policy registry.
5. Job discovery results.
6. Job detail and fit score rationale.
7. Tailored CV diff viewer.
8. Review queue.
9. Manual handoff packet.
10. Application tracker.
11. Analytics.
12. Settings and autonomy controls.

## 15. autonomy controls

User-configurable controls:

- Maximum applications per day/week.
- Minimum match score for drafting.
- Minimum match score for assisted apply.
- Minimum match score for autonomous apply.
- Allowed sources for autofill.
- Allowed sources for auto-submit.
- Required approval for salary questions.
- Required approval for work authorisation questions.
- Required approval for diversity/disability questions.
- Required approval for legal declarations.
- Quiet hours.
- Notification preferences.

## 16. safety, compliance, and trust requirements

Hard prohibitions:

- No CAPTCHA bypass.
- No bot-detection evasion.
- No unauthorised access.
- No fake identities.
- No fabricated employment history, credentials, dates, salary, or authorisation status.
- No automated submission to denylisted sites.
- No high-risk personal answers without explicit user rule or approval.

Privacy requirements:

- Encrypt sensitive data at rest.
- Encrypt in transit.
- Store only necessary candidate data.
- Allow export and deletion.
- Separate raw CV files from derived evidence.
- Log document access.
- Avoid storing session cookies unless absolutely necessary and explicitly approved.

Audit requirements:

- Every generated document must store model, prompt version, source evidence, and validation result.
- Every form field submitted must store field label, answer, source of answer, confidence, and approval status.
- Every policy block must store reason and evidence.

## 17. testing strategy

### 17.1 unit tests

- Salary parser.
- Location parser.
- Job deduplication.
- Source policy decisions.
- Evidence retrieval.
- Claim validation.
- ATS readability checks.
- Form question risk classifier.

### 17.2 integration tests

- Adapter extraction against recorded fixtures.
- End-to-end discovery to score.
- CV generation with unsupported claim blocker.
- Manual handoff packet generation.
- Browser automation against local mock forms.

### 17.3 evaluation tests

Create a small gold dataset:

- 50 job descriptions.
- Expected extracted fields.
- Expected match scores.
- Expected CV evidence matches.
- Expected form risk labels.

Track:

- extraction accuracy;
- false positive job matches;
- unsupported claim rate;
- form classification accuracy;
- submission-block correctness;
- cost per processed job.

## 18. observability

Log and trace:

- crawl run ID;
- source adapter;
- extraction path;
- model calls;
- token cost;
- output validation failures;
- approval gates;
- browser actions;
- retries;
- policy decisions;
- user edits;
- final application outcomes.

Dashboards:

- jobs discovered per source;
- extraction failure rate;
- low-confidence fields;
- generated documents blocked by claim validation;
- applications by status;
- cost per application;
- interview conversion by source;
- browser automation failure reasons.

## 19. prompt and schema management

Create versioned prompt files:

```text
/prompts/source_assessment_v1.md
/prompts/job_extraction_v1.md
/prompts/fit_rationale_v1.md
/prompts/cv_tailoring_v1.md
/prompts/claim_validation_v1.md
/prompts/form_question_classification_v1.md
/prompts/cover_letter_v1.md
```

Rules:

- Prompts must be versioned.
- Generated artefacts must store prompt version.
- Schema changes require migration and tests.
- Agent outputs must be parsed into Pydantic models.
- Invalid outputs must retry with structured error feedback.

## 20. Codex working instructions

When implementing, Codex should follow this order:

1. Build deterministic infrastructure first.
2. Add schemas before agents.
3. Add tests before LLM-dependent behaviour.
4. Prefer adapters and structured extraction over browser automation.
5. Keep browser actions behind policy checks.
6. Store provenance for every extracted field.
7. Store evidence mappings for every generated claim.
8. Never allow submission without passing policy, confidence, and approval gates.
9. Avoid large magical prompts; use small specialist prompts with typed outputs.
10. Create fixtures for every external source adapter.

## 21. initial backlog

### epic 1 — foundations

- Create monorepo.
- Add Docker Compose.
- Add FastAPI app.
- Add Next.js app.
- Add Postgres and Redis.
- Add migrations.
- Add auth placeholder.
- Add audit event service.

### epic 2 — source and policy layer

- Create source tables.
- Create policy engine.
- Add robots cache.
- Add domain allow/deny rules.
- Add policy admin UI.

### epic 3 — discovery adapters

- Add adapter interface.
- Add Greenhouse adapter.
- Add Lever adapter.
- Add Ashby adapter.
- Add Workable adapter.
- Add SmartRecruiters adapter.
- Add JSON-LD adapter.
- Add static HTML adapter.

### epic 4 — job intelligence

- Add extraction pipeline.
- Add normalisers.
- Add dedupe.
- Add scoring.
- Add job list UI.
- Add job detail UI.

### epic 5 — candidate evidence and tailoring

- Add CV upload.
- Add evidence extraction.
- Add evidence editor.
- Add CV tailoring.
- Add claim validator.
- Add `.docx` export.
- Add CV diff viewer.

### epic 6 — review and handoff

- Add review queue.
- Add approval requests.
- Add handoff packet.
- Add application tracker.

### epic 7 — browser automation

- Add Playwright worker.
- Add Stagehand wrapper.
- Add mock application form tests.
- Add form schema extractor.
- Add autofill with pause-before-submit.

### epic 8 — analytics

- Add outcome tracking.
- Add funnel dashboard.
- Add source performance dashboard.
- Add CV variant analytics.

## 22. recommended repository structure

```text
job-finder-agent/
  apps/
    api/
      app/
        api/
        core/
        db/
        models/
        schemas/
        services/
        agents/
        workflows/
        adapters/
        document_generation/
        browser/
        tests/
    web/
      app/
      components/
      lib/
      tests/
  workers/
    discovery_worker/
    extraction_worker/
    tailoring_worker/
    browser_worker/
  packages/
    shared-schemas/
  prompts/
  fixtures/
    greenhouse/
    lever/
    ashby/
    workable/
    smartrecruiters/
    json_ld/
    mock_forms/
  infra/
    docker/
    migrations/
  docs/
    architecture.md
    source_policy.md
    autonomy_model.md
    evaluation_plan.md
```

## 23. first Codex prompt

Use this as the opening prompt to Codex:

```text
You are building a governed job-search agent and application orchestration platform.

Start by creating the repository foundation for the MVP described in docs/job_finder_codex_development_plan.md.

Implement phase 0 and phase 1 only:
- monorepo structure;
- FastAPI backend;
- Next.js frontend shell;
- Docker Compose with Postgres and Redis;
- Alembic migrations;
- SQLAlchemy/SQLModel database models for candidate profiles, evidence, sources, source policies, job postings, generated documents, applications, approvals, and audit events;
- Pydantic API schemas;
- health endpoint;
- audit event helper;
- basic tests.

Do not implement live crawling, browser automation, or LLM calls yet.

Acceptance criteria:
- docker compose up starts the stack;
- API health endpoint returns OK;
- migrations run from an empty database;
- tests pass;
- README explains local setup;
- no external secrets are committed.
```

## 24. key decision log

| Decision | Choice | Rationale |
|---|---|---|
| Product posture | Governed agent, not blind auto-apply bot | Reduces risk and improves trust |
| Backend | Python FastAPI | Best fit for NLP, agents, extraction, and analytics |
| Frontend | Next.js/TypeScript | Strong dashboard and review UX |
| Workflow runtime | LangGraph | Durable execution, checkpoints, human-in-the-loop |
| Agent layer | OpenAI Agents SDK + typed tools | Handoffs, guardrails, tracing, structured model calls |
| Structured validation | Pydantic | Testable typed outputs |
| Browser automation | Playwright + Stagehand | Deterministic automation plus AI resilience |
| Database | PostgreSQL + pgvector | Unified relational and semantic storage for MVP |
| Source strategy | API-first | More reliable, cheaper, and more compliant than scraping |
| Submission strategy | Assisted first, autonomous later | Safer development path |

## 25. near-term build recommendation

Build in this order:

1. Data model and audit spine.
2. Source policy registry.
3. ATS API adapters.
4. Job extraction and scoring.
5. Evidence bank.
6. Factually grounded CV tailoring.
7. Review queue and handoff packet.
8. Controlled browser autofill.
9. Governed autonomous submission.
10. Outcome analytics.

The spine of the system is not the crawler. The spine is the audit-backed decision graph. Once that is solid, crawling, tailoring, and browser automation become replaceable skills rather than existential risks.

## 26. reference sources used for stack and design research

- LangGraph durable execution: https://docs.langchain.com/oss/python/langgraph/durable-execution
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangChain human-in-the-loop middleware: https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- OpenAI Agents SDK tracing: https://openai.github.io/openai-agents-python/tracing/
- OpenAI Agents SDK guardrails: https://openai.github.io/openai-agents-python/guardrails/
- OpenAI Agents guide: https://developers.openai.com/api/docs/guides/agents
- Pydantic AI structured output: https://pydantic.dev/docs/ai/core-concepts/output/
- Pydantic AI tool/function concepts: https://pydantic.dev/docs/ai/tools-toolsets/tools/
- Stagehand product page: https://www.browserbase.com/stagehand
- Stagehand docs: https://docs.stagehand.dev/v3/first-steps/introduction
- Stagehand Playwright integration: https://docs.stagehand.dev/v3/integrations/playwright
- Greenhouse Job Board API: https://developers.greenhouse.io/job-board.html
- Ashby job board API examples: https://www.ashbyhq.com/job-board-embed-examples
- Public ATS API overview: https://cavuno.com/blog/ats-platforms-public-job-posting-apis
- Job data aggregator example: https://theirstack.com/en/job-posting-api
- Indeed legal terms: https://www.indeed.com/legal
- Google JobPosting structured data: https://developers.google.com/search/docs/appearance/structured-data/job-posting
- Schema.org JobPosting: https://schema.org/JobPosting
```
