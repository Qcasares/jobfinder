export type ApprovalDataSource = "api" | "local";
export type ApprovalRequestStatus = "pending" | "approved" | "rejected" | "needs_changes";

export type ApprovalRequestItem = {
  id: string;
  jobPostingId: string;
  userId: string;
  requestType: string;
  status: ApprovalRequestStatus;
  reason: string;
  reviewerId: string | null;
  decisionReason: string | null;
  requestedAt: string;
  resolvedAt: string | null;
  synthetic: boolean;
  sideEffect: "manual_record_only";
};

export type ApprovalSummary = {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  needsChanges: number;
};

export type ApprovalSnapshot = {
  source: ApprovalDataSource;
  detail: string;
  checkedUrl?: string;
  summary: ApprovalSummary;
  requests: ApprovalRequestItem[];
};

type ApiApprovalSummary = {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  needs_changes: number;
};

type ApiApprovalRequest = {
  id: string;
  review_item_id: string;
  job_posting_id: string;
  requester_id: string;
  request_type: string;
  status: ApprovalRequestStatus;
  reason: string;
  reviewer_id: string | null;
  requested_at: string;
  resolved_at: string | null;
  safety: {
    submit_performed: boolean;
    autofill_performed: boolean;
    application_created: boolean;
  };
};

export async function getApprovalSnapshot(): Promise<ApprovalSnapshot> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return localApprovalSnapshot(
      "NEXT_PUBLIC_API_BASE_URL is not configured; synthetic approval data is shown."
    );
  }

  const summaryUrl = new URL("/approvals/summary", apiBaseUrl).toString();
  const requestsUrl = new URL("/approvals/requests", apiBaseUrl).toString();

  try {
    const [summaryResponse, requestsResponse] = await Promise.all([
      fetch(summaryUrl, { cache: "no-store", headers: { accept: "application/json" } }),
      fetch(requestsUrl, { cache: "no-store", headers: { accept: "application/json" } })
    ]);

    if (!summaryResponse.ok || !requestsResponse.ok) {
      return localApprovalSnapshot(
        `Approval API returned HTTP ${summaryResponse.status}/${requestsResponse.status}; synthetic approval data is shown.`,
        requestsUrl
      );
    }

    const summary = (await summaryResponse.json()) as ApiApprovalSummary;
    const requests = ((await requestsResponse.json()) as ApiApprovalRequest[]).map(
      mapApiApprovalRequest
    );

    return {
      source: "api",
      detail: "Approval requests are loaded from the FastAPI manual-review endpoints.",
      checkedUrl: requestsUrl,
      summary: {
        total: summary.total,
        pending: summary.pending,
        approved: summary.approved,
        rejected: summary.rejected,
        needsChanges: summary.needs_changes
      },
      requests
    };
  } catch {
    return localApprovalSnapshot(
      "Approval API is unreachable; synthetic approval data is shown.",
      requestsUrl
    );
  }
}

function mapApiApprovalRequest(item: ApiApprovalRequest): ApprovalRequestItem {
  return {
    id: item.id,
    jobPostingId: item.job_posting_id,
    userId: item.requester_id,
    requestType: item.request_type,
    status: item.status,
    reason: item.reason,
    reviewerId: item.reviewer_id,
    decisionReason: item.status === "pending" ? null : item.reason,
    requestedAt: item.requested_at,
    resolvedAt: item.resolved_at,
    synthetic: true,
    sideEffect:
      item.safety.submit_performed ||
      item.safety.autofill_performed ||
      item.safety.application_created
        ? "manual_record_only"
        : "manual_record_only"
  };
}

function localApprovalSnapshot(detail: string, checkedUrl?: string): ApprovalSnapshot {
  const requests: ApprovalRequestItem[] = [
    {
      id: "approval-local-policy",
      jobPostingId: "local:review-policy-ambiguity",
      userId: "local-user",
      requestType: "source_policy_review",
      status: "pending",
      reason: "Reviewer must confirm source policy before downstream drafting.",
      reviewerId: null,
      decisionReason: null,
      requestedAt: "2026-04-30T09:00:00Z",
      resolvedAt: null,
      synthetic: true,
      sideEffect: "manual_record_only"
    },
    {
      id: "approval-local-claim",
      jobPostingId: "local:ready-greenhouse-fixture",
      userId: "local-user",
      requestType: "claim_evidence_review",
      status: "needs_changes",
      reason: "Generated claims need explicit evidence mapping before drafting can continue.",
      reviewerId: "reviewer-local",
      decisionReason: "Add evidence references for every claim.",
      requestedAt: "2026-04-30T09:10:00Z",
      resolvedAt: "2026-04-30T09:20:00Z",
      synthetic: true,
      sideEffect: "manual_record_only"
    }
  ];

  return {
    source: "local",
    detail,
    checkedUrl,
    summary: buildApprovalSummary(requests),
    requests
  };
}

function buildApprovalSummary(requests: readonly ApprovalRequestItem[]): ApprovalSummary {
  return {
    total: requests.length,
    pending: requests.filter((request) => request.status === "pending").length,
    approved: requests.filter((request) => request.status === "approved").length,
    rejected: requests.filter((request) => request.status === "rejected").length,
    needsChanges: requests.filter((request) => request.status === "needs_changes").length
  };
}
