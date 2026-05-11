import { afterEach, describe, expect, it, vi } from "vitest";
import { getApprovalSnapshot } from "./approval-data";

describe("getApprovalSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses an empty local approval state when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getApprovalSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary).toEqual({
      total: 0,
      pending: 0,
      approved: 0,
      rejected: 0,
      needsChanges: 0
    });
    expect(snapshot.requests).toHaveLength(0);
    expect(snapshot.detail).toContain("no approval requests");
  });
});
