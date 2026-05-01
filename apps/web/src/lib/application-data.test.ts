import { afterEach, describe, expect, it, vi } from "vitest";
import { getApplicationSnapshot } from "./application-data";

describe("getApplicationSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses synthetic local application tracker data when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getApplicationSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary).toMatchObject({
      total: 0,
      submitted: 0,
      externalSideEffects: 0
    });
    expect(snapshot.applications).toEqual([]);
  });
});
