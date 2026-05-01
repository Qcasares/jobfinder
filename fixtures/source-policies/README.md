# Source Policy Fixtures

Fixtures in this directory support deterministic tests for the phase 2 source registry and policy engine. They must be synthetic, reduced, and safe to publish.

Allowed examples include:

- invented domains, source identifiers, and policy records;
- synthetic action matrices for `discover`, `extract`, `draft`, `autofill`, and `submit`;
- fake robots cache records for invented domains;
- artificial policy evidence references that do not point to private or scraped content;
- small examples for allowed, denied, and manual-review decisions.

Do not store real terms snapshots, copied terms text, cookies, scraped pages, screenshots, browser traces, private job-board responses, API payloads from real accounts, secrets, tokens, candidate files, or employer-specific private data.

When modeling a real-world platform posture, encode only the intended synthetic behavior. For example, tests may include an invented source marked as prohibited, but they must not include real platform terms text or captured pages.
