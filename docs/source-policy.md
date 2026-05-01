# Source Policy

Phase 2 introduces the source registry and policy engine boundary for Jobfinder. This is a governance layer only: it decides whether an intended action is allowed, blocked, or requires manual review before any crawler, adapter, LLM, browser, or submission feature exists.

## Deny-By-Default Model

Source automation is denied unless a registry entry explicitly allows the exact action being requested. Unknown sources, missing policies, expired policy evidence, ambiguous terms, CAPTCHA or bot-detection requirements, login-only access, identity checks, or platform-specific prohibitions must block automation and route the workflow to manual review.

The action enum is:

- `discover`: finding job listings or references from an approved source.
- `extract`: reading structured job details from an approved source.
- `draft`: preparing candidate-facing materials or answers using approved evidence.
- `autofill`: placing approved answers into a form without submitting it.
- `submit`: sending an application or final form action.

Allowing one action never implies another. A source may allow `discover` and `extract` while still blocking `draft`, `autofill`, and `submit`.

## Source Registry

The source registry records the current policy posture for each source or source family. Entries should be explicit enough to support deterministic policy checks and audit review. At minimum, registry data should capture:

- source identifier and canonical domain or API family;
- allowed, denied, or review-required actions;
- policy evidence type, such as official API docs, published terms, partner agreement, or internal manual approval;
- evidence URL or internal reference, recorded without copying real terms text into fixtures;
- last reviewed timestamp and reviewer;
- notes explaining constraints, confidence, or required handoff conditions.

LinkedIn and Indeed are known prohibited examples for automated discovery, extraction, autofill, and submission in the default registry posture. Treat them as blocked unless a future explicit, reviewed, written authorization path exists.

## Robots Cache

The robots cache stores fetched or derived robots.txt decisions for approved sources so policy checks can avoid repeated network reads and provide stable provenance. It is not a permission grant. Robots allowance is only one input; source terms, API authorization, platform restrictions, and manual approvals remain controlling.

Fixtures and tests must not store real robots.txt snapshots. Use synthetic domains and synthetic rule text only.

## Manual Review Posture

Manual review is the required fallback when policy confidence is low or a requested action is materially risky. Reviewers should see the source, requested action, policy evidence, confidence reason, and recommended safe next step. Manual review may approve a bounded action, keep the action blocked, or request updated policy evidence. It must not be used to bypass CAPTCHA, bot detection, access controls, or platform prohibitions.

## Audit Emission

Every policy decision must emit an append-only audit event before downstream workflow progress. Audit payloads should include:

- source identifier and normalized URL or API family;
- requested action;
- decision: allowed, denied, or manual review required;
- policy version or registry record identifier;
- evidence references used for the decision;
- reason code and human-readable rationale;
- reviewer identity when a manual decision is involved;
- correlation identifiers linking the policy decision to discovery, extraction, draft, autofill, or submission workflow events.

Audit records should contain metadata and references, not raw private pages, cookies, tokens, real scraped terms text, or candidate secrets.
