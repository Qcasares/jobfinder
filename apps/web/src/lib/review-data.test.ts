import { afterEach, describe, expect, it, vi } from "vitest";
import { getReviewQueueSnapshot } from "./review-data";

describe("getReviewQueueSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses an empty local live-review state when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getReviewQueueSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary).toEqual({ total: 0, ready: 0, needsReview: 0 });
    expect(snapshot.items).toHaveLength(0);
    expect(snapshot.detail).toContain("no live review queue records");
  });
});
