import { afterEach, describe, expect, it, vi } from "vitest";
import { getSettingsSnapshot } from "./settings-data";

describe("getSettingsSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses safe local runtime posture when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getSettingsSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.runtime.externalIntegrationsEnabled).toBe(false);
    expect(snapshot.runtime.secretsLoaded).toBe(false);
    expect(snapshot.runtime.capabilities).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: "live_crawling", enabled: false }),
        expect.objectContaining({ key: "llm_calls", enabled: false }),
        expect.objectContaining({ key: "autofill_submit", enabled: false })
      ])
    );
  });
});
