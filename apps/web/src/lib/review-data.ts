import { dashboardData, type ReviewQueueItem as ReviewQueueBucket } from "./dashboard-data";

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

type ApiReviewSummary = {
  total: number;
  ready: number;
  needs_review: number;
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
      "NEXT_PUBLIC_API_BASE_URL is not configured; synthetic dashboard data is shown."
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
        `Review API returned HTTP ${summaryResponse.status}/${queueResponse.status}; synthetic dashboard data is shown.`,
        queueUrl
      );
    }

    const summary = (await summaryResponse.json()) as ApiReviewSummary;
    const items = ((await queueResponse.json()) as ApiReviewItem[]).map(mapApiReviewItem);

    return {
      source: "api",
      detail: "Review queue data is loaded from the FastAPI synthetic fixture endpoints.",
      checkedUrl: queueUrl,
      summary: {
        total: summary.total,
        ready: summary.ready,
        needsReview: summary.needs_review
      },
      items,
      buckets: buildBuckets(items)
    };
  } catch {
    return localReviewQueueSnapshot("Review API is unreachable; synthetic dashboard data is shown.", queueUrl);
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
  const items: ReviewJobItem[] = [
    {
      id: "local:review-policy-ambiguity",
      source: "local-fixture",
      externalId: "review-policy-ambiguity",
      title: "Policy ambiguity sample",
      company: "Synthetic Careers Ltd",
      locations: ["Remote - UK"],
      remoteType: "remote",
      salaryMin: null,
      salaryMax: null,
      salaryCurrency: null,
      employmentType: "full_time",
      postedDate: null,
      validThrough: null,
      requiredSkills: ["Python", "SQL"],
      preferredSkills: ["FastAPI"],
      reviewStatus: "needs_review",
      reviewReasons: ["Source policy and provenance require manual review."],
      extractionConfidence: 0.72,
      provenanceHints: {
        title: {
          fieldName: "title",
          source: "local_dashboard_fixture",
          confidence: 0.72,
          note: "Synthetic fallback item; not a scraped posting."
        }
      },
      synthetic: true,
      dataOrigin: "local_dashboard_fixture",
      fixtureName: null
    },
    {
      id: "local:ready-greenhouse-fixture",
      source: "greenhouse",
      externalId: "ready-greenhouse-fixture",
      title: "Backend Engineer fixture",
      company: "Acme Robotics",
      locations: ["London, UK"],
      remoteType: "onsite",
      salaryMin: 100000,
      salaryMax: 120000,
      salaryCurrency: "USD",
      employmentType: "full_time",
      postedDate: "2026-03-01",
      validThrough: null,
      requiredSkills: ["Python", "SQL"],
      preferredSkills: [],
      reviewStatus: "ready",
      reviewReasons: [],
      extractionConfidence: 0.96,
      provenanceHints: {
        title: {
          fieldName: "title",
          source: "structured_adapter",
          confidence: 0.96,
          note: "Synthetic fallback item; not a scraped posting."
        }
      },
      synthetic: true,
      dataOrigin: "local_dashboard_fixture",
      fixtureName: null
    }
  ];

  return {
    source: "local",
    detail,
    checkedUrl,
    summary: {
      total: items.length,
      ready: items.filter((item) => item.reviewStatus === "ready").length,
      needsReview: items.filter((item) => item.reviewStatus === "needs_review").length
    },
    items,
    buckets: dashboardData.reviewQueue
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
