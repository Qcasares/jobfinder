# Automation Roadmap

This roadmap brings live automation capabilities into scope in the order they can be made governed, auditable, and reversible. Each phase must keep unknown sources denied by default and must ship with tests, runtime flags, audit events, and operator-visible status.

## Phase A: Live Intake

Current phase. Operators submit one approved HTTPS job URL. The API checks `discover` and `extract`, fetches within strict limits, extracts deterministic job data, and routes results to review. No broad crawling, login, LLM, browser automation, autofill, or submit behavior is included.

## Phase B: Approved Search-Result Discovery

Add queued discovery for approved sources only. Requirements: per-source allowlist, robots/terms evidence, crawl budgets, rate limits, retry/backoff limits, dedupe, audit correlation, and review dashboards. Prohibited platforms and unknown sources stay blocked.

## Phase C: Candidate Vault And Evidence Controls

Initial implementation: Jobfinder can register metadata-only candidate document records behind `JOBFINDER_API_CANDIDATE_VAULT_ENABLED=true`. Records require a `vault://` storage reference, content hash, byte size, MIME type, consent scope, and retention period. The app database does not store document bytes, third-party credentials, or inline CV text. Redaction starts as pending and extraction approval is false by default.

Next controls before document content can drive workflow: encrypted object storage integration, delete/export endpoints, redaction review, approved evidence extraction, and UI review for vault records. No model prompts or application fields should receive document content unless evidence records are approved.

## Phase D: LLM-Assisted Drafting

Initial implementation: Jobfinder can create review-required drafting packets behind `JOBFINDER_API_LLM_DRAFTING_ENABLED=true`. Requests must name a review item and approved candidate evidence records. The source must allow `draft`, provider output must map every claim back to the requested evidence ids, and audit events record metadata without raw prompt or draft text. Drafts cannot autofill, submit, or create applications.

Next controls before production use: real model-provider configuration, prompt redaction, token/cost accounting, reviewer decision workflow for draft packets, and provider-specific safety tests.

## Phase E: Browser Autofill

Initial implementation: Jobfinder can prepare dry-run autofill packets behind `JOBFINDER_API_AUTOFILL_PACKETS_ENABLED=true`. Packets require a review-required drafting run and an `autofill` source-policy allowance for the exact target URL domain. The packet stores field previews and provenance, emits audit metadata, and is always review-required. Browser automation, real autofill, application creation, and submit remain false.

Next controls before browser execution: exact form approval records, isolated browser session runtime, stop-before-submit enforcement in the browser runner, field-level screenshots or DOM evidence, and action-time operator confirmation.

## Phase F: Submission

Initial implementation: Jobfinder can prepare final-review packets behind `JOBFINDER_API_SUBMISSION_PACKETS_ENABLED=true`. Packets require an autofill packet, an explicit `ready_for_final_review` operator confirmation, and a source-policy `submit` allowance for the target domain. They can store rollback/withdrawal notes and emit immutable audit metadata. They do not submit, create applications, or perform any external side effect.

Next controls before actual submission: final packet approval workflow, action-time operator confirmation, source-specific submission runner, post-submit verification, and rollback/withdrawal procedures.

## Phase G: Login-Gated Sources And Credentials

Add login-gated access only with first-party user authorization, secure token or credential storage, revocation, least-privilege access, and log redaction. CAPTCHA, bot detection, identity checks, and access controls remain stop conditions that route to manual handoff. The system may detect and record them; it must not bypass them.
