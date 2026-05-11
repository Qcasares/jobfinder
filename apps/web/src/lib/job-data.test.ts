import { afterEach, describe, expect, it, vi } from "vitest";
import { getJobCatalogSnapshot } from "./job-data";

describe("getJobCatalogSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses an empty local live-job state when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getJobCatalogSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary).toMatchObject({ total: 0, ready: 0, needsReview: 0 });
    expect(snapshot.jobs).toHaveLength(0);
    expect(snapshot.detail).toContain("no live jobs are shown");
  });
});
