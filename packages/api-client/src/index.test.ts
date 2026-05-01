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
