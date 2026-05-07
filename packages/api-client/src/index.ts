export type FetchLike = (
  input: string,
  init?: {
    body?: string;
    headers?: Record<string, string>;
    method?: string;
  }
) => Promise<Response>;

export type JobfinderApiClientOptions = {
  baseUrl: string;
  fetch?: FetchLike;
};

export type HealthResponse = {
  status: "ok";
  service: string;
};

export type SourcePolicyAction = "discover" | "extract" | "draft" | "autofill" | "submit";

export type SourcePolicyCheckRequest = {
  source?: string;
  domain: string;
  action: SourcePolicyAction;
};

export type SourcePolicyDecision = {
  action: SourcePolicyAction;
  allowed: boolean;
  reason: string;
  status: string;
  confidence: number;
  review_status: string;
};

export type RuntimeCapability = {
  key: string;
  label: string;
  enabled: boolean;
  detail: string;
};

export type RuntimeSettingsResponse = {
  service_name: string;
  environment: string;
  audit_schema_version: number;
  database_configured: boolean;
  redis_configured: boolean;
  secrets_loaded: boolean;
  external_integrations_enabled: boolean;
  capabilities: RuntimeCapability[];
};

export type LiveDiscoveryStatus =
  | "requested"
  | "denied"
  | "fetched"
  | "discovered"
  | "extracted"
  | "failed";

export type LiveDiscoveryRequest = {
  url: string;
  source_domain?: string;
  requested_by?: string;
};

export type LiveSearchDiscoveryRequest = LiveDiscoveryRequest & {
  max_results?: number;
};

export type LiveDiscoveryRun = {
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

export class JobfinderApiError extends Error {
  readonly status: number;
  readonly url: string;
  readonly body: unknown;

  constructor(message: string, options: { status: number; url: string; body: unknown }) {
    super(message);
    this.name = "JobfinderApiError";
    this.status = options.status;
    this.url = options.url;
    this.body = options.body;
  }
}

export class JobfinderApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: FetchLike;

  constructor(options: JobfinderApiClientOptions) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl);
    this.fetchImpl = options.fetch ?? fetch;
  }

  getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  getRuntimeSettings(): Promise<RuntimeSettingsResponse> {
    return this.request<RuntimeSettingsResponse>("/settings/runtime");
  }

  checkSourcePolicy(request: SourcePolicyCheckRequest): Promise<SourcePolicyDecision> {
    return this.request<SourcePolicyDecision>("/source-policies/check", {
      body: JSON.stringify(request),
      headers: { accept: "application/json", "content-type": "application/json" },
      method: "POST"
    });
  }

  createLiveDiscoveryRun(request: LiveDiscoveryRequest): Promise<LiveDiscoveryRun> {
    return this.request<LiveDiscoveryRun>("/live-discovery/runs", {
      body: JSON.stringify(request),
      headers: { accept: "application/json", "content-type": "application/json" },
      method: "POST"
    });
  }

  createLiveSearchDiscoveryRun(
    request: LiveSearchDiscoveryRequest
  ): Promise<LiveDiscoveryRun> {
    return this.request<LiveDiscoveryRun>("/live-discovery/search-runs", {
      body: JSON.stringify(request),
      headers: { accept: "application/json", "content-type": "application/json" },
      method: "POST"
    });
  }

  private async request<T>(
    path: string,
    init: {
      body?: string;
      headers?: Record<string, string>;
      method?: string;
    } = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await this.fetchImpl(url, {
      headers: init.headers ?? { accept: "application/json" },
      method: init.method ?? "GET",
      ...(init.body === undefined ? {} : { body: init.body })
    });
    const body = await parseResponseBody(response);

    if (!response.ok) {
      throw new JobfinderApiError(`Jobfinder API request failed with ${response.status}`, {
        body,
        status: response.status,
        url
      });
    }

    return body as T;
  }
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim();
  if (!trimmed) {
    throw new Error("Jobfinder API baseUrl is required.");
  }
  return trimmed.replace(/\/+$/, "");
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}
