import { afterEach, describe, expect, it, vi } from "vitest";
import { getJobCatalogSnapshot } from "./job-data";

describe("getJobCatalogSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses synthetic local job data when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getJobCatalogSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary).toMatchObject({ total: 1, ready: 1, needsReview: 0 });
    expect(snapshot.jobs.every((job) => job.synthetic)).toBe(true);
    expect(snapshot.jobs[0].fixtureName).toBe("greenhouse_missing_salary.json");
  });
});
