import { afterEach, describe, expect, it, vi } from "vitest";
import { getCandidateWorkspaceSnapshot } from "./candidate-data";

describe("getCandidateWorkspaceSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses synthetic local candidate data when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getCandidateWorkspaceSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.profile.synthetic).toBe(true);
    expect(snapshot.evidence).toHaveLength(2);
    expect(snapshot.searchCriteria).toHaveLength(1);
    expect(snapshot.safetyNote).toContain("Synthetic local candidate workspace");
  });
});
