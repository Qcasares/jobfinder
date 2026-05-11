export type SourcePolicyStatus = "allowed" | "manual_only" | "blocked";

export const sourcePolicyActions = [
  "discover",
  "extract",
  "draft",
  "autofill",
  "submit"
] as const;

export type SourcePolicyAction = (typeof sourcePolicyActions)[number];

export type SourcePolicy = {
  name: string;
  domain: string;
  type:
    | "ATS API"
    | "Public Job Board"
    | "Structured JobPosting"
    | "Manual Review"
    | "Prohibited Platform";
  status: SourcePolicyStatus;
  confidence?: number;
  reviewStatus?: "approved" | "needs_review" | "prohibited";
  allowedActions: SourcePolicyAction[];
  deniedActions: SourcePolicyAction[];
  reason: string;
};

export type SourcePolicyCheckInput = {
  source?: string;
  domain?: string;
  action: SourcePolicyAction;
};

export type SourcePolicyDecision = {
  action: SourcePolicyAction;
  allowed: boolean;
  reason: string;
  policy: SourcePolicy;
};

export type PipelineColumn = {
  label: string;
  count: number;
  description: string;
};

export type ReviewQueueItem = {
  label: string;
  count: number;
  risk: "low" | "medium" | "high";
};

export type AuditEvent = {
  id: string;
  actor: "system" | "reviewer" | "policy";
  action: string;
  subject: string;
  provenance: string;
  occurredAt: string;
};

export const dashboardData = {
  sourcePolicies: [
    {
      name: "Greenhouse",
      domain: "greenhouse.io",
      type: "ATS API",
      status: "allowed",
      confidence: 0.96,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract", "draft"],
      deniedActions: ["autofill", "submit"],
      reason: "Official ATS API intake is approved for discovery, extraction, and drafting only."
    },
    {
      name: "Lever",
      domain: "lever.co",
      type: "ATS API",
      status: "allowed",
      confidence: 0.94,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract", "draft"],
      deniedActions: ["autofill", "submit"],
      reason: "Official ATS API intake is approved for discovery, extraction, and drafting only."
    },
    {
      name: "Ashby",
      domain: "ashbyhq.com",
      type: "ATS API",
      status: "allowed",
      confidence: 0.92,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract", "draft"],
      deniedActions: ["autofill", "submit"],
      reason: "Official ATS API intake is approved for discovery, extraction, and drafting only."
    },
    {
      name: "Reed",
      domain: "reed.co.uk",
      type: "Public Job Board",
      status: "allowed",
      confidence: 0.82,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract"],
      deniedActions: ["draft", "autofill", "submit"],
      reason:
        "Approved for bounded operator-queued public page discovery and extraction only; stop on login, CAPTCHA, bot detection, or access controls."
    },
    {
      name: "Hays",
      domain: "hays.co.uk",
      type: "Public Job Board",
      status: "allowed",
      confidence: 0.82,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract"],
      deniedActions: ["draft", "autofill", "submit"],
      reason:
        "Approved for bounded operator-queued public page discovery and extraction only; stop on login, CAPTCHA, bot detection, or access controls."
    },
    {
      name: "Totaljobs",
      domain: "totaljobs.com",
      type: "Public Job Board",
      status: "allowed",
      confidence: 0.82,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract"],
      deniedActions: ["draft", "autofill", "submit"],
      reason:
        "Approved for bounded operator-queued public page discovery and extraction only; stop on login, CAPTCHA, bot detection, or access controls."
    },
    {
      name: "CityJobs",
      domain: "cityjobs.com",
      type: "Public Job Board",
      status: "allowed",
      confidence: 0.82,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract"],
      deniedActions: ["draft", "autofill", "submit"],
      reason:
        "Approved for bounded operator-queued public page discovery and extraction only; stop on login, CAPTCHA, bot detection, or access controls."
    },
    {
      name: "eFinancialCareers",
      domain: "efinancialcareers.co.uk",
      type: "Public Job Board",
      status: "allowed",
      confidence: 0.82,
      reviewStatus: "approved",
      allowedActions: ["discover", "extract"],
      deniedActions: ["draft", "autofill", "submit"],
      reason:
        "Approved for bounded operator-queued public page discovery and extraction only; stop on login, CAPTCHA, bot detection, or access controls."
    },
    {
      name: "Company careers",
      domain: "careers.example.com",
      type: "Structured JobPosting",
      status: "manual_only",
      confidence: 0.78,
      reviewStatus: "needs_review",
      allowedActions: ["extract", "draft"],
      deniedActions: ["discover", "autofill", "submit"],
      reason: "Structured JobPosting data can support extraction and drafting after provenance review."
    },
    {
      name: "Unknown source",
      domain: "unverified.example",
      type: "Manual Review",
      status: "manual_only",
      confidence: 0.42,
      reviewStatus: "needs_review",
      allowedActions: [],
      deniedActions: ["discover", "extract", "draft", "autofill", "submit"],
      reason: "Unknown sources have no allowed actions until source policy review is completed."
    },
    {
      name: "Indeed",
      domain: "indeed.com",
      type: "Prohibited Platform",
      status: "blocked",
      confidence: 0.99,
      reviewStatus: "prohibited",
      allowedActions: [],
      deniedActions: ["discover", "extract", "draft", "autofill", "submit"],
      reason:
        "Indeed is not enabled for automated discovery in Jobfinder; use manual review or an approved official integration only."
    },
    {
      name: "LinkedIn",
      domain: "linkedin.com",
      type: "Prohibited Platform",
      status: "blocked",
      confidence: 0.98,
      reviewStatus: "prohibited",
      allowedActions: [],
      deniedActions: ["discover", "extract", "draft", "autofill", "submit"],
      reason:
        "No automation or submission is allowed for LinkedIn unless an approved official integration exists."
    }
  ] satisfies SourcePolicy[],
  pipeline: [
    {
      label: "Discovered",
      count: 12,
      description: "Postings queued from approved sources"
    },
    {
      label: "Extracted",
      count: 8,
      description: "Structured fields captured with provenance"
    },
    {
      label: "Scored",
      count: 6,
      description: "Fit rationale ready for reviewer inspection"
    },
    {
      label: "Needs Review",
      count: 7,
      description: "Policy, confidence, or claim gates require approval"
    },
    {
      label: "Ready",
      count: 5,
      description: "Application drafts staged, not submitted"
    }
  ] satisfies PipelineColumn[],
  reviewQueue: [
    { label: "Policy ambiguity", count: 6, risk: "high" },
    { label: "Low extraction confidence", count: 4, risk: "medium" },
    { label: "Unmapped generated claim", count: 3, risk: "high" },
    { label: "Form answer needs approval", count: 2, risk: "medium" },
    { label: "Salary/location normalization", count: 2, risk: "low" }
  ] satisfies ReviewQueueItem[],
  auditFeed: [
    {
      id: "audit-1005",
      actor: "system",
      action: "Source policy evaluated",
      subject: "greenhouse-intake",
      provenance: "source-policy:v0 source:greenhouse-board",
      occurredAt: "09:42"
    },
    {
      id: "audit-1004",
      actor: "policy",
      action: "Submission blocked",
      subject: "indeed-apply",
      provenance: "policy-registry:v0 prohibited_action:submit",
      occurredAt: "09:38"
    },
    {
      id: "audit-1003",
      actor: "system",
      action: "Extraction confidence recorded",
      subject: "ashby-role",
      provenance: "json_ld:JobPosting field_provenance:required_skills",
      occurredAt: "09:27"
    },
    {
      id: "audit-1002",
      actor: "reviewer",
      action: "Claim evidence requested",
      subject: "tailored-cover-letter-draft",
      provenance: "claim-validation:v0 evidence_bank:approved",
      occurredAt: "09:14"
    },
    {
      id: "audit-1001",
      actor: "system",
      action: "Draft held for approval",
      subject: "lever-application",
      provenance: "approval-gate:v0 risk:medium",
      occurredAt: "09:03"
    }
  ] satisfies AuditEvent[]
} as const;

export function getSourcePolicySummary(policies: readonly SourcePolicy[]) {
  return policies.reduce(
    (summary, policy) => {
      summary[policy.status === "manual_only" ? "manualOnly" : policy.status] += 1;
      return summary;
    },
    { allowed: 0, manualOnly: 0, blocked: 0 }
  );
}

export function getPipelineTotal(columns: readonly PipelineColumn[]) {
  return columns.reduce((total, column) => total + column.count, 0);
}

export function getReviewQueueTotal(items: readonly ReviewQueueItem[]) {
  return items.reduce((total, item) => total + item.count, 0);
}

export function evaluateSourcePolicyLocally(
  input: SourcePolicyCheckInput,
  policies: readonly SourcePolicy[] = dashboardData.sourcePolicies
): SourcePolicyDecision {
  const policy = findSourcePolicy(input, policies) ?? buildUnknownSourcePolicy(input);
  const allowed = policy.allowedActions.includes(input.action);
  const reason = allowed
    ? `${policy.name} allows ${input.action} with governed review gates.`
    : policy.reason;

  return {
    action: input.action,
    allowed,
    reason,
    policy
  };
}

export function findSourcePolicy(
  input: Pick<SourcePolicyCheckInput, "source" | "domain">,
  policies: readonly SourcePolicy[] = dashboardData.sourcePolicies
) {
  const sourceName = input.source?.trim().toLowerCase();
  const domain = normalizeDomain(input.domain);

  return policies.find((policy) => {
    const policyDomain = normalizeDomain(policy.domain);
    const matchesName = sourceName ? policy.name.toLowerCase() === sourceName : false;
    const matchesDomain = domain
      ? domain === policyDomain || domain.endsWith(`.${policyDomain}`)
      : false;

    return matchesName || matchesDomain;
  });
}

export function normalizeDomain(domain?: string) {
  const normalized = domain
    ?.trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0];

  return normalized || undefined;
}

function buildUnknownSourcePolicy(input: SourcePolicyCheckInput): SourcePolicy {
  const domain = normalizeDomain(input.domain) ?? "unverified.example";

  return {
    name: input.source?.trim() || domain,
    domain,
    type: "Manual Review",
    status: "manual_only",
    confidence: 0,
    reviewStatus: "needs_review",
    allowedActions: [],
    deniedActions: [...sourcePolicyActions],
    reason: "Source is not in the approved registry; all actions require manual review."
  };
}
