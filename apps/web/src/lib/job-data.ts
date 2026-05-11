export type JobDataSource = "api" | "local";

export type JobItem = {
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
  sourceUrl: string;
  applicationUrl: string | null;
  reviewStatus: "ready" | "needs_review";
  reviewReasons: string[];
  extractionConfidence: number;
  requiredSkills: string[];
  preferredSkills: string[];
  fixtureName: string | null;
  synthetic: boolean;
};

export type JobSummary = {
  total: number;
  ready: number;
  needsReview: number;
  remote: number;
  hybrid: number;
  onsite: number;
  unknownRemote: number;
};

export type JobCatalogSnapshot = {
  source: JobDataSource;
  detail: string;
  checkedUrl?: string;
  summary: JobSummary;
  jobs: JobItem[];
};

type ApiJobItem = {
  id: string;
  source: string;
  external_id: string;
  title: string;
  company: string;
  locations: string[];
  remote_type: JobItem["remoteType"];
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  employment_type: string | null;
  posted_date: string | null;
  valid_through: string | null;
  source_url: string;
  application_url: string | null;
  review_status: JobItem["reviewStatus"];
  review_reasons: string[];
  extraction_confidence: number;
  required_skills: string[];
  preferred_skills: string[];
  fixture_name: string | null;
  synthetic: boolean;
};

type ApiJobSummary = {
  total: number;
  ready: number;
  needs_review: number;
  remote: number;
  hybrid: number;
  onsite: number;
  unknown_remote: number;
};

export async function getJobCatalogSnapshot(): Promise<JobCatalogSnapshot> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return localJobCatalogSnapshot(
      "NEXT_PUBLIC_API_BASE_URL is not configured; no live jobs are shown."
    );
  }

  const jobsUrl = new URL("/jobs", apiBaseUrl).toString();
  const summaryUrl = new URL("/jobs/summary", apiBaseUrl).toString();

  try {
    const [jobsResponse, summaryResponse] = await Promise.all([
      fetch(jobsUrl, { cache: "no-store", headers: { accept: "application/json" } }),
      fetch(summaryUrl, { cache: "no-store", headers: { accept: "application/json" } })
    ]);

    if (!jobsResponse.ok || !summaryResponse.ok) {
      return localJobCatalogSnapshot(
        `Jobs API returned HTTP ${jobsResponse.status}/${summaryResponse.status}; no live jobs are shown.`,
        jobsUrl
      );
    }

    const jobs = ((await jobsResponse.json()) as ApiJobItem[]).map(mapApiJobItem);
    const summary = (await summaryResponse.json()) as ApiJobSummary;

    return {
      source: "api",
      detail:
        "Live jobs are loaded from approved intake records; placeholder records stay hidden from the primary workflow.",
      checkedUrl: jobsUrl,
      summary: {
        total: summary.total,
        ready: summary.ready,
        needsReview: summary.needs_review,
        remote: summary.remote,
        hybrid: summary.hybrid,
        onsite: summary.onsite,
        unknownRemote: summary.unknown_remote
      },
      jobs
    };
  } catch {
    return localJobCatalogSnapshot("Jobs API is unreachable; no live jobs are shown.", jobsUrl);
  }
}

function mapApiJobItem(job: ApiJobItem): JobItem {
  return {
    id: job.id,
    source: job.source,
    externalId: job.external_id,
    title: job.title,
    company: job.company,
    locations: job.locations,
    remoteType: job.remote_type,
    salaryMin: job.salary_min,
    salaryMax: job.salary_max,
    salaryCurrency: job.salary_currency,
    employmentType: job.employment_type,
    postedDate: job.posted_date,
    validThrough: job.valid_through,
    sourceUrl: job.source_url,
    applicationUrl: job.application_url,
    reviewStatus: job.review_status,
    reviewReasons: job.review_reasons,
    extractionConfidence: job.extraction_confidence,
    requiredSkills: job.required_skills,
    preferredSkills: job.preferred_skills,
    fixtureName: job.fixture_name,
    synthetic: job.synthetic
  };
}

function localJobCatalogSnapshot(detail: string, checkedUrl?: string): JobCatalogSnapshot {
  return {
    source: "local",
    detail,
    checkedUrl,
    summary: {
      total: 0,
      ready: 0,
      needsReview: 0,
      remote: 0,
      hybrid: 0,
      onsite: 0,
      unknownRemote: 0
    },
    jobs: []
  };
}
