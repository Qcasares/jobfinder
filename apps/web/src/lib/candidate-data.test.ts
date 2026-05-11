import { afterEach, describe, expect, it, vi } from "vitest";
import { getCandidateWorkspaceSnapshot } from "./candidate-data";

describe("getCandidateWorkspaceSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses a disconnected local candidate state when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getCandidateWorkspaceSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.profile.synthetic).toBe(true);
    expect(snapshot.profile.profileName).toBe("Candidate profile not connected");
    expect(snapshot.evidence).toHaveLength(0);
    expect(snapshot.searchCriteria).toHaveLength(0);
    expect(snapshot.safetyNote).toContain("approved evidence");
  });
});
