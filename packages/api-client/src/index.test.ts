import { describe, expect, it, vi } from "vitest";
import { JobfinderApiClient, JobfinderApiError } from "./index";

describe("JobfinderApiClient", () => {
  it("fetches health from the configured API base URL", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ status: "ok", service: "jobfinder-api" }));
    const client = new JobfinderApiClient({
      baseUrl: "http://127.0.0.1:8000/",
      fetch: fetchMock
    });

    await expect(client.getHealth()).resolves.toEqual({
      status: "ok",
      service: "jobfinder-api"
    });
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/health", {
      headers: { accept: "application/json" },
      method: "GET"
    });
  });

  it("checks source policy decisions through the governed API endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        action: "submit",
        allowed: false,
        reason: "Submit is disabled by policy.",
        status: "denied",
        confidence: 0.98,
        review_status: "reviewed"
      })
    );
    const client = new JobfinderApiClient({
      baseUrl: "http://127.0.0.1:8000",
      fetch: fetchMock
    });

    const decision = await client.checkSourcePolicy({
      domain: "linkedin.com",
      action: "submit"
    });

    expect(decision.allowed).toBe(false);
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/source-policies/check", {
      body: JSON.stringify({ domain: "linkedin.com", action: "submit" }),
      headers: { accept: "application/json", "content-type": "application/json" },
      method: "POST"
    });
  });

  it("starts governed live discovery runs", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        id: "run-1",
        url: "https://careers.example.test/jobs/platform",
        final_url: "https://careers.example.test/jobs/platform",
        source_domain: "careers.example.test",
        requested_by: "operator-test",
        status: "extracted",
        fetched_status_code: 200,
        content_type: "text/html",
        extracted_count: 1,
        review_item_ids: ["json-ld:live-platform-1"],
        discovered_count: 0,
        discovered_urls: [],
        manual_handoff_id: null,
        failure: null
      })
    );
    const client = new JobfinderApiClient({
      baseUrl: "http://127.0.0.1:8000",
      fetch: fetchMock
    });

    const run = await client.createLiveDiscoveryRun({
      url: "https://careers.example.test/jobs/platform",
      source_domain: "careers.example.test",
      requested_by: "operator-test"
    });

    expect(run.status).toBe("extracted");
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/live-discovery/runs", {
      body: JSON.stringify({
        url: "https://careers.example.test/jobs/platform",
        source_domain: "careers.example.test",
        requested_by: "operator-test"
      }),
      headers: { accept: "application/json", "content-type": "application/json" },
      method: "POST"
    });
  });

  it("starts governed search-result discovery runs", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        id: "run-2",
        url: "https://careers.example.test/search?q=engineer",
        final_url: "https://careers.example.test/search?q=engineer",
        source_domain: "careers.example.test",
        requested_by: "operator-test",
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
        manual_handoff_id: null,
        failure: null
      })
    );
    const client = new JobfinderApiClient({
      baseUrl: "http://127.0.0.1:8000",
      fetch: fetchMock
    });

    const run = await client.createLiveSearchDiscoveryRun({
      url: "https://careers.example.test/search?q=engineer",
      source_domain: "careers.example.test",
      requested_by: "operator-test",
      max_results: 5
    });

    expect(run.status).toBe("discovered");
    expect(run.discovered_urls).toHaveLength(2);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/live-discovery/search-runs",
      {
        body: JSON.stringify({
          url: "https://careers.example.test/search?q=engineer",
          source_domain: "careers.example.test",
          requested_by: "operator-test",
          max_results: 5
        }),
        headers: { accept: "application/json", "content-type": "application/json" },
        method: "POST"
      }
    );
  });

  it("throws a typed error for non-2xx API responses", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ detail: "not found" }, { status: 404 }));
    const client = new JobfinderApiClient({
      baseUrl: "http://127.0.0.1:8000",
      fetch: fetchMock
    });

    await expect(client.getRuntimeSettings()).rejects.toMatchObject({
      name: "JobfinderApiError",
      status: 404,
      url: "http://127.0.0.1:8000/settings/runtime"
    });
  });

  it("does not expose submit, autofill, crawl, or LLM helpers", () => {
    const client = new JobfinderApiClient({
      baseUrl: "http://127.0.0.1:8000",
      fetch: vi.fn()
    }) as unknown as Record<string, unknown>;

    expect(client.submitApplication).toBeUndefined();
    expect(client.autofillApplication).toBeUndefined();
    expect(client.crawlSource).toBeUndefined();
    expect(client.generateWithLlm).toBeUndefined();
  });
});

function jsonResponse(payload: unknown, init: { status?: number } = {}): Response {
  return new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json" },
    status: init.status ?? 200
  });
}

void JobfinderApiError;
