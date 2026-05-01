import { afterEach, describe, expect, it, vi } from "vitest";
import { getReviewQueueSnapshot } from "./review-data";

describe("getReviewQueueSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses synthetic local review data when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getReviewQueueSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary).toEqual({ total: 2, ready: 1, needsReview: 1 });
    expect(snapshot.items.every((item) => item.synthetic)).toBe(true);
    expect(snapshot.items.some((item) => item.reviewStatus === "needs_review")).toBe(true);
  });
});
