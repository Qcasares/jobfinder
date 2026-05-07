import type { JobItem } from "@/lib/job-data";

export type MatchFilter = "all" | "remote" | "hybrid" | "onsite" | "ready";

export type SearchFormState = {
  query: string;
  location: string;
};

export function filterJobMatches(
  jobs: readonly JobItem[],
  search: SearchFormState,
  activeFilter: MatchFilter
) {
  const queryTerms = tokenize(search.query);
  const locationTerms = tokenize(search.location);

  return jobs.filter((job) => {
    const searchableText = normalizeText([
      job.title,
      job.company,
      job.source,
      job.remoteType,
      job.employmentType,
      ...job.locations,
      ...job.requiredSkills,
      ...job.preferredSkills
    ]);
    const locationText = normalizeText([job.remoteType, ...job.locations]);
    const queryMatches =
      queryTerms.length === 0 || queryTerms.some((term) => searchableText.includes(term));
    const locationMatches =
      locationTerms.length === 0 || locationTerms.some((term) => locationText.includes(term));
    const filterMatches =
      activeFilter === "all" ||
      (activeFilter === "remote" && job.remoteType === "remote") ||
      (activeFilter === "hybrid" && job.remoteType === "hybrid") ||
      (activeFilter === "onsite" && job.remoteType === "onsite") ||
      (activeFilter === "ready" && job.reviewStatus === "ready");

    return queryMatches && locationMatches && filterMatches;
  });
}

function tokenize(value: string) {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .map((term) => term.trim())
    .filter(Boolean);
}

function normalizeText(values: Array<string | null | undefined>) {
  return values.filter(Boolean).join(" ").toLowerCase();
}
