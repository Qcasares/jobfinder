export type LiveDiscoveryStatus =
  | "requested"
  | "denied"
  | "fetched"
  | "discovered"
  | "extracted"
  | "failed";

export type LiveDiscoveryRequest = {
  url: string;
  sourceDomain?: string;
  requestedBy?: string;
};

export type LiveSearchDiscoveryRequest = LiveDiscoveryRequest & {
  maxResults?: number;
};

export type LiveDiscoveryRun = {
  id: string;
  url: string;
  finalUrl: string | null;
  sourceDomain: string;
  requestedBy: string;
  status: LiveDiscoveryStatus;
  fetchedStatusCode: number | null;
  contentType: string | null;
  extractedCount: number;
  reviewItemIds: string[];
  discoveredCount: number;
  discoveredUrls: string[];
  failure: {
    reason: string;
    detail: string;
  } | null;
};

type ApiLiveDiscoveryRun = {
  id: string;
  url: string;
  final_url: string | null;
  source_domain: string;
  requested_by: string;
  status: LiveDiscoveryStatus;
  fetched_status_code: number | null;
  content_type: string | null;
  extracted_count: number;
  review_item_ids: string[];
  discovered_count: number;
  discovered_urls: string[];
  failure: {
    reason: string;
    detail: string;
  } | null;
};

export async function createLiveDiscoveryRun(
  request: LiveDiscoveryRequest
): Promise<LiveDiscoveryRun> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!apiBaseUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured.");
  }

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/live-discovery/runs`, {
    method: "POST",
    headers: { accept: "application/json", "content-type": "application/json" },
    body: JSON.stringify({
      url: request.url,
      source_domain: request.sourceDomain || undefined,
      requested_by: request.requestedBy || "dashboard-operator"
    })
  });
  const payload = (await response.json()) as ApiLiveDiscoveryRun | { detail?: string };

  if (!response.ok) {
    const detail = "detail" in payload && payload.detail ? payload.detail : response.statusText;
    throw new Error(`Live discovery returned HTTP ${response.status}: ${detail}`);
  }

  return mapLiveDiscoveryRun(payload as ApiLiveDiscoveryRun);
}

export async function createLiveSearchDiscoveryRun(
  request: LiveSearchDiscoveryRequest
): Promise<LiveDiscoveryRun> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!apiBaseUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured.");
  }

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/live-discovery/search-runs`, {
    method: "POST",
    headers: { accept: "application/json", "content-type": "application/json" },
    body: JSON.stringify({
      url: request.url,
      source_domain: request.sourceDomain || undefined,
      requested_by: request.requestedBy || "dashboard-operator",
      max_results: request.maxResults ?? 25
    })
  });
  const payload = (await response.json()) as ApiLiveDiscoveryRun | { detail?: string };

  if (!response.ok) {
    const detail = "detail" in payload && payload.detail ? payload.detail : response.statusText;
    throw new Error(`Live search discovery returned HTTP ${response.status}: ${detail}`);
  }

  return mapLiveDiscoveryRun(payload as ApiLiveDiscoveryRun);
}

function mapLiveDiscoveryRun(run: ApiLiveDiscoveryRun): LiveDiscoveryRun {
  return {
    id: run.id,
    url: run.url,
    finalUrl: run.final_url,
    sourceDomain: run.source_domain,
    requestedBy: run.requested_by,
    status: run.status,
    fetchedStatusCode: run.fetched_status_code,
    contentType: run.content_type,
    extractedCount: run.extracted_count,
    reviewItemIds: run.review_item_ids,
    discoveredCount: run.discovered_count,
    discoveredUrls: run.discovered_urls,
    failure: run.failure
  };
}
