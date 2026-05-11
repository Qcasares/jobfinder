import { afterEach, describe, expect, it, vi } from "vitest";
import { enqueueDiscoveryQueueRun } from "./operator-control-data";

describe("enqueueDiscoveryQueueRun", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("posts operator-approved discovery queue requests with bearer auth", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test/");
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          id: "queue-1",
          mode: "search",
          url: "https://careers.example.test/jobs/search?q=engineer",
          source_domain: "careers.example.test",
          requested_by: "dashboard-operator",
          status: "queued",
          max_results: 5,
          attempts: 0,
          max_attempts: 3,
          rate_limit_after: null,
          live_run_id: null,
          manual_handoff_id: null,
          failure_reason: null,
          failure_detail: null,
          discovered_urls: [],
          review_item_ids: [],
          created_at: "2026-05-11T08:00:00Z",
          updated_at: "2026-05-11T08:00:00Z"
        }),
        { headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await enqueueDiscoveryQueueRun("operator-token", {
      maxResults: 5,
      mode: "search",
      requestedBy: "dashboard-operator",
      sourceDomain: "careers.example.test",
      url: "https://careers.example.test/jobs/search?q=engineer"
    });

    expect(run.status).toBe("queued");
    expect(fetchMock).toHaveBeenCalledWith("https://api.example.test/discovery-queue/runs", {
      method: "POST",
      headers: {
        accept: "application/json",
        authorization: "Bearer operator-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        url: "https://careers.example.test/jobs/search?q=engineer",
        source_domain: "careers.example.test",
        mode: "search",
        requested_by: "dashboard-operator",
        max_results: 5,
        max_attempts: 3
      })
    });
  });
});
