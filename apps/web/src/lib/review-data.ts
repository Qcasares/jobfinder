import type { ReviewQueueItem as ReviewQueueBucket } from "./dashboard-data";

export type ReviewStatus = "ready" | "needs_review";
export type ReviewDataSource = "api" | "local";

export type ReviewProvenanceHint = {
  fieldName: string;
  source: string;
  confidence: number;
  note: string;
};

export type ReviewJobItem = {
  id: string;
  source: string;
  externalId: string;
  title: string;
  company: string;
  locations: string[];
  remoteType: "remote" | "hybrid" | "onsite" | "unknown";
  salaryMin: number | null;
  salaryMax: number | null;
  salaryCurrency: string | null;
  employmentType: string | null;
  postedDate: string | null;
  validThrough: string | null;
  requiredSkills: string[];
  preferredSkills: string[];
  reviewStatus: ReviewStatus;
  reviewReasons: string[];
  extractionConfidence: number;
  provenanceHints: Record<string, ReviewProvenanceHint>;
  synthetic: boolean;
  dataOrigin: "synthetic_adapter_fixture" | "synthetic_raw_posting" | "local_dashboard_fixture";
  fixtureName: string | null;
};

export type ReviewQueueSummary = {
  total: number;
  ready: number;
  needsReview: number;
};

export type ReviewQueueSnapshot = {
  source: ReviewDataSource;
  detail: string;
  checkedUrl?: string;
  summary: ReviewQueueSummary;
  items: ReviewJobItem[];
  buckets: ReviewQueueBucket[];
};

type ApiReviewItem = {
  id: string;
  source: string;
  external_id: string;
  title: string;
  company: string;
  locations: string[];
  remote_type: ReviewJobItem["remoteType"];
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  employment_type: string | null;
  posted_date: string | null;
  valid_through: string | null;
  required_skills: string[];
  preferred_skills: string[];
  review_status: ReviewStatus;
  review_reasons: string[];
  extraction_confidence: number;
  provenance_hints: Record<
    string,
    {
      field_name: string;
      source: string;
      confidence: number;
      note: string;
    }
  >;
  synthetic: boolean;
  data_origin: ReviewJobItem["dataOrigin"];
  fixture_name: string | null;
};

export async function getReviewQueueSnapshot(): Promise<ReviewQueueSnapshot> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return localReviewQueueSnapshot(
      "NEXT_PUBLIC_API_BASE_URL is not configured; no live review queue records are shown."
    );
  }

  const summaryUrl = new URL("/review/summary", apiBaseUrl).toString();
  const queueUrl = new URL("/review/queue", apiBaseUrl).toString();

  try {
    const [summaryResponse, queueResponse] = await Promise.all([
      fetch(summaryUrl, { cache: "no-store", headers: { accept: "application/json" } }),
      fetch(queueUrl, { cache: "no-store", headers: { accept: "application/json" } })
    ]);

    if (!summaryResponse.ok || !queueResponse.ok) {
      return localReviewQueueSnapshot(
        `Review API returned HTTP ${summaryResponse.status}/${queueResponse.status}; no live review queue records are shown.`,
        queueUrl
      );
    }

    const items = ((await queueResponse.json()) as ApiReviewItem[]).map(mapApiReviewItem);
    const liveItems = items.filter((item) => !item.synthetic);

    return {
      source: "api",
      detail: "Review queue data is loaded from approved intake and extraction records.",
      checkedUrl: queueUrl,
      summary: {
        total: liveItems.length,
        ready: liveItems.filter((item) => item.reviewStatus === "ready").length,
        needsReview: liveItems.filter((item) => item.reviewStatus === "needs_review").length
      },
      items,
      buckets: buildBuckets(liveItems)
    };
  } catch {
    return localReviewQueueSnapshot(
      "Review API is unreachable; no live review queue records are shown.",
      queueUrl
    );
  }
}

function mapApiReviewItem(item: ApiReviewItem): ReviewJobItem {
  return {
    id: item.id,
    source: item.source,
    externalId: item.external_id,
    title: item.title,
    company: item.company,
    locations: item.locations,
    remoteType: item.remote_type,
    salaryMin: item.salary_min,
    salaryMax: item.salary_max,
    salaryCurrency: item.salary_currency,
    employmentType: item.employment_type,
    postedDate: item.posted_date,
    validThrough: item.valid_through,
    requiredSkills: item.required_skills,
    preferredSkills: item.preferred_skills,
    reviewStatus: item.review_status,
    reviewReasons: item.review_reasons,
    extractionConfidence: item.extraction_confidence,
    provenanceHints: Object.fromEntries(
      Object.entries(item.provenance_hints).map(([field, hint]) => [
        field,
        {
          fieldName: hint.field_name,
          source: hint.source,
          confidence: hint.confidence,
          note: hint.note
        }
      ])
    ),
    synthetic: item.synthetic,
    dataOrigin: item.data_origin,
    fixtureName: item.fixture_name
  };
}

function localReviewQueueSnapshot(detail: string, checkedUrl?: string): ReviewQueueSnapshot {
  return {
    source: "local",
    detail,
    checkedUrl,
    summary: {
      total: 0,
      ready: 0,
      needsReview: 0
    },
    items: [],
    buckets: buildBuckets([])
  };
}

function buildBuckets(items: readonly ReviewJobItem[]): ReviewQueueBucket[] {
  const lowConfidence = items.filter((item) => item.extractionConfidence < 0.8).length;
  const missingSalary = items.filter((item) => item.salaryMin === null && item.salaryMax === null).length;
  const ready = items.filter((item) => item.reviewStatus === "ready").length;
  const needsReview = items.filter((item) => item.reviewStatus === "needs_review").length;

  return [
    { label: "Needs manual review", count: needsReview, risk: needsReview > 0 ? "high" : "low" },
    { label: "Low extraction confidence", count: lowConfidence, risk: lowConfidence > 0 ? "medium" : "low" },
    { label: "Salary/location normalization", count: missingSalary, risk: missingSalary > 0 ? "low" : "low" },
    { label: "Ready with provenance", count: ready, risk: "low" }
  ];
}
