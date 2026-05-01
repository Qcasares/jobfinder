export type ApplicationDataSource = "api" | "local";
export type ApplicationStatus =
  | "not_started"
  | "ready_for_review"
  | "approved"
  | "submitted"
  | "withdrawn";

export type ApplicationItem = {
  id: string;
  jobPostingId: string;
  approvalRequestId: string | null;
  jobTitle: string;
  company: string;
  status: ApplicationStatus;
  applicationUrl: string | null;
  submittedAt: string | null;
  createdAt: string;
  updatedAt: string;
  synthetic: boolean;
  safety: {
    submitPerformed: boolean;
    autofillPerformed: boolean;
    externalSideEffect: boolean;
  };
};

export type ApplicationSummary = {
  total: number;
  notStarted: number;
  inReview: number;
  approved: number;
  submitted: number;
  externalSideEffects: number;
};

export type ApplicationSnapshot = {
  source: ApplicationDataSource;
  detail: string;
  checkedUrl?: string;
  summary: ApplicationSummary;
  applications: ApplicationItem[];
};

type ApiApplicationItem = {
  id: string;
  job_posting_id: string;
  approval_request_id: string | null;
  job_title: string;
  company: string;
  status: ApplicationStatus;
  application_url: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
  synthetic: boolean;
  safety: {
    submit_performed: boolean;
    autofill_performed: boolean;
    external_side_effect: boolean;
  };
};

type ApiApplicationSummary = {
  total: number;
  not_started: number;
  in_review: number;
  approved: number;
  submitted: number;
  external_side_effects: number;
};

export async function getApplicationSnapshot(): Promise<ApplicationSnapshot> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return localApplicationSnapshot(
      "NEXT_PUBLIC_API_BASE_URL is not configured; no application records are shown."
    );
  }

  const applicationsUrl = new URL("/applications", apiBaseUrl).toString();
  const summaryUrl = new URL("/applications/summary", apiBaseUrl).toString();

  try {
    const [applicationsResponse, summaryResponse] = await Promise.all([
      fetch(applicationsUrl, { cache: "no-store", headers: { accept: "application/json" } }),
      fetch(summaryUrl, { cache: "no-store", headers: { accept: "application/json" } })
    ]);

    if (!applicationsResponse.ok || !summaryResponse.ok) {
      return localApplicationSnapshot(
        `Applications API returned HTTP ${applicationsResponse.status}/${summaryResponse.status}; no application records are shown.`,
        applicationsUrl
      );
    }

    const applications = ((await applicationsResponse.json()) as ApiApplicationItem[]).map(
      mapApiApplication
    );
    const summary = (await summaryResponse.json()) as ApiApplicationSummary;

    return {
      source: "api",
      detail: "Applications are read-only tracker records. No submit or autofill endpoint is enabled.",
      checkedUrl: applicationsUrl,
      summary: {
        total: summary.total,
        notStarted: summary.not_started,
        inReview: summary.in_review,
        approved: summary.approved,
        submitted: summary.submitted,
        externalSideEffects: summary.external_side_effects
      },
      applications
    };
  } catch {
    return localApplicationSnapshot(
      "Applications API is unreachable; no application records are shown.",
      applicationsUrl
    );
  }
}

function mapApiApplication(item: ApiApplicationItem): ApplicationItem {
  return {
    id: item.id,
    jobPostingId: item.job_posting_id,
    approvalRequestId: item.approval_request_id,
    jobTitle: item.job_title,
    company: item.company,
    status: item.status,
    applicationUrl: item.application_url,
    submittedAt: item.submitted_at,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    synthetic: item.synthetic,
    safety: {
      submitPerformed: item.safety.submit_performed,
      autofillPerformed: item.safety.autofill_performed,
      externalSideEffect: item.safety.external_side_effect
    }
  };
}

function localApplicationSnapshot(detail: string, checkedUrl?: string): ApplicationSnapshot {
  return {
    source: "local",
    detail,
    checkedUrl,
    summary: {
      total: 0,
      notStarted: 0,
      inReview: 0,
      approved: 0,
      submitted: 0,
      externalSideEffects: 0
    },
    applications: []
  };
}
