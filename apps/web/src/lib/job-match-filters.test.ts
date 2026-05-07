import { describe, expect, it } from "vitest";
import { filterJobMatches } from "@/lib/job-match-filters";
import type { JobItem } from "@/lib/job-data";

const baseJob: JobItem = {
  id: "job-1",
  source: "greenhouse",
  externalId: "fixture-1",
  title: "Backend Engineer",
  company: "Acme Robotics",
  locations: ["London, UK"],
  remoteType: "onsite",
  salaryMin: null,
  salaryMax: null,
  salaryCurrency: null,
  employmentType: "full_time",
  postedDate: null,
  validThrough: null,
  sourceUrl: "https://example.test/jobs/1",
  applicationUrl: null,
  reviewStatus: "ready",
  reviewReasons: [],
  extractionConfidence: 1,
  requiredSkills: ["Python", "SQL"],
  preferredSkills: [],
  fixtureName: "greenhouse_missing_salary.json",
  synthetic: true
};

const remoteJob: JobItem = {
  ...baseJob,
  id: "job-2",
  title: "Platform Engineer",
  locations: ["Remote - US"],
  remoteType: "remote",
  salaryMin: 120000,
  salaryMax: 150000
};

const reviewJob: JobItem = {
  ...baseJob,
  id: "job-3",
  title: "Data Analyst",
  company: "Initech",
  reviewStatus: "needs_review",
  requiredSkills: ["Analytics"]
};

describe("filterJobMatches", () => {
  it("returns the full synthetic match set until a search is applied", () => {
    expect(filterJobMatches([baseJob, remoteJob], { query: "", location: "" }, "all")).toHaveLength(
      2
    );
  });

  it("matches role terms across title and skill text", () => {
    expect(
      filterJobMatches([baseJob, remoteJob, reviewJob], { query: "python", location: "" }, "all")
    ).toEqual([baseJob, remoteJob]);
  });

  it("combines location and status filters", () => {
    expect(
      filterJobMatches([baseJob, remoteJob, reviewJob], { query: "", location: "Remote" }, "ready")
    ).toEqual([remoteJob]);
  });
});
