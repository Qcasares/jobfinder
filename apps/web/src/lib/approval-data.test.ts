import { afterEach, describe, expect, it, vi } from "vitest";
import { getApprovalSnapshot } from "./approval-data";

describe("getApprovalSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses synthetic local approval data when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getApprovalSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary).toEqual({
      total: 2,
      pending: 1,
      approved: 0,
      rejected: 0,
      needsChanges: 1
    });
    expect(snapshot.requests.every((request) => request.synthetic)).toBe(true);
    expect(snapshot.requests.every((request) => request.sideEffect === "manual_record_only")).toBe(
      true
    );
  });
});
