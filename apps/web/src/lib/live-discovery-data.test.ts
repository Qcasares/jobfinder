import { afterEach, describe, expect, it, vi } from "vitest";
import { createLiveDiscoveryRun, createLiveSearchDiscoveryRun } from "./live-discovery-data";

describe("createLiveDiscoveryRun", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("posts operator-provided URLs to the governed live discovery endpoint", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://127.0.0.1:8000/");
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          id: "run-1",
          url: "https://careers.example.test/jobs/platform",
          final_url: "https://careers.example.test/jobs/platform",
          source_domain: "careers.example.test",
          requested_by: "dashboard-operator",
          status: "extracted",
          fetched_status_code: 200,
          content_type: "text/html",
          extracted_count: 1,
          review_item_ids: ["json-ld:live-platform-1"],
          discovered_count: 0,
          discovered_urls: [],
          failure: null
        }),
        { headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await createLiveDiscoveryRun({
      url: "https://careers.example.test/jobs/platform",
      sourceDomain: "careers.example.test"
    });

    expect(run.status).toBe("extracted");
    expect(run.extractedCount).toBe(1);
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/live-discovery/runs", {
      method: "POST",
      headers: { accept: "application/json", "content-type": "application/json" },
      body: JSON.stringify({
        url: "https://careers.example.test/jobs/platform",
        source_domain: "careers.example.test",
        requested_by: "dashboard-operator"
      })
    });
  });

  it("posts search pages to the governed search-result discovery endpoint", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://127.0.0.1:8000/");
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          id: "run-2",
          url: "https://careers.example.test/search?q=engineer",
          final_url: "https://careers.example.test/search?q=engineer",
          source_domain: "careers.example.test",
          requested_by: "dashboard-operator",
          status: "discovered",
          fetched_status_code: 200,
          content_type: "text/html",
          extracted_count: 0,
          review_item_ids: [],
          discovered_count: 2,
          discovered_urls: [
            "https://careers.example.test/jobs/platform",
            "https://careers.example.test/jobs/data"
          ],
          failure: null
        }),
        { headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await createLiveSearchDiscoveryRun({
      url: "https://careers.example.test/search?q=engineer",
      sourceDomain: "careers.example.test",
      maxResults: 5
    });

    expect(run.status).toBe("discovered");
    expect(run.discoveredUrls).toHaveLength(2);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/live-discovery/search-runs",
      {
        method: "POST",
        headers: { accept: "application/json", "content-type": "application/json" },
        body: JSON.stringify({
          url: "https://careers.example.test/search?q=engineer",
          source_domain: "careers.example.test",
          requested_by: "dashboard-operator",
          max_results: 5
        })
      }
    );
  });

  it("fails closed when the API URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    await expect(
      createLiveDiscoveryRun({ url: "https://careers.example.test/jobs/platform" })
    ).rejects.toThrow("NEXT_PUBLIC_API_BASE_URL is not configured.");
  });
});
