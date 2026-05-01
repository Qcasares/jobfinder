import { afterEach, describe, expect, it, vi } from "vitest";
import { getAuditSnapshot } from "./audit-data";

describe("getAuditSnapshot", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses synthetic local audit data when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    const snapshot = await getAuditSnapshot();

    expect(snapshot.source).toBe("local");
    expect(snapshot.summary.total).toBe(5);
    expect(snapshot.summary.chainValid).toBe(true);
    expect(snapshot.events.every((event) => event.payload.synthetic === true)).toBe(true);
    expect(snapshot.events[0].eventHash).toContain("synthetic-");
  });
});
