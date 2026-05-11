export type OperatorToken = {
  accessToken: string;
  actorId: string;
  expiresAt: string;
};

export type ManualHandoff = {
  id: string;
  url: string;
  sourceDomain: string;
  triggerType: string;
  requestedBy: string;
  status: "open" | "resolved";
  detectionDetail: string;
  runId: string | null;
  createdAt: string;
  resolvedAt: string | null;
};

export type DiscoveryQueueRun = {
  id: string;
  mode: "job" | "search";
  url: string;
  sourceDomain: string;
  requestedBy: string;
  status: string;
  attempts: number;
  maxAttempts: number;
  rateLimitAfter: string | null;
  liveRunId: string | null;
  manualHandoffId: string | null;
  failureReason: string | null;
  discoveredUrls: string[];
  reviewItemIds: string[];
  createdAt: string;
};

export type DiscoveryQueueRunRequest = {
  url: string;
  sourceDomain?: string;
  mode: "job" | "search";
  requestedBy: string;
  maxResults: number;
  maxAttempts?: number;
};

export type ObservabilitySummary = {
  totalAuditEvents: number;
  errorEvents: number;
  openManualHandoffs: number;
  queuedDiscoveryRuns: number;
  failedDiscoveryRuns: number;
  auditChainValid: boolean;
  latestAuditHash: string | null;
  activeAlerts: ObservabilityAlert[];
};

export type ObservabilityAlert = {
  id: string;
  severity: "info" | "warning" | "critical";
  title: string;
  detail: string;
  recommendedAction: string;
};

export type SourceRecord = {
  id: string;
  name: string;
  domain: string;
  sourceType: string;
  policyStatus: string | null;
};

export type SourcePolicyAttachment = {
  sourceId: string;
  status: string;
  reason: string;
  allowedActions: string[];
  deniedActions: string[];
};

type ApiOperatorToken = {
  access_token: string;
  actor_id: string;
  expires_at: string;
};

type ApiManualHandoff = {
  id: string;
  url: string;
  source_domain: string;
  trigger_type: string;
  requested_by: string;
  status: "open" | "resolved";
  detection_detail: string;
  run_id: string | null;
  created_at: string;
  resolved_at: string | null;
};

type ApiDiscoveryQueueRun = {
  id: string;
  mode: "job" | "search";
  url: string;
  source_domain: string;
  requested_by: string;
  status: string;
  attempts: number;
  max_attempts: number;
  rate_limit_after: string | null;
  live_run_id: string | null;
  manual_handoff_id: string | null;
  failure_reason: string | null;
  discovered_urls: string[];
  review_item_ids: string[];
  created_at: string;
};

type ApiObservabilitySummary = {
  total_audit_events: number;
  error_events: number;
  open_manual_handoffs: number;
  queued_discovery_runs: number;
  failed_discovery_runs: number;
  audit_chain_valid: boolean;
  latest_audit_hash: string | null;
  active_alerts: ApiObservabilityAlert[];
};

type ApiObservabilityAlert = {
  id: string;
  severity: "info" | "warning" | "critical";
  title: string;
  detail: string;
  recommended_action: string;
};

type ApiSourceRecord = {
  id: string;
  name: string;
  domain: string;
  source_type: string;
  latest_policy: { status: string } | null;
};

export async function createOperatorToken(
  loginSecret: string,
  actorId: string
): Promise<OperatorToken> {
  const payload = await request<ApiOperatorToken>("/auth/operator-token", {
    body: JSON.stringify({ login_secret: loginSecret, actor_id: actorId }),
    headers: { "content-type": "application/json" },
    method: "POST"
  });
  return {
    accessToken: payload.access_token,
    actorId: payload.actor_id,
    expiresAt: payload.expires_at
  };
}

export async function getManualHandoffs(): Promise<ManualHandoff[]> {
  const payload = await request<ApiManualHandoff[]>("/manual-handoffs?status=open");
  return payload.map(mapManualHandoff);
}

export async function resolveManualHandoff(
  token: string,
  recordId: string,
  reviewerId: string
): Promise<ManualHandoff> {
  const payload = await request<ApiManualHandoff>(`/manual-handoffs/${recordId}/resolve`, {
    body: JSON.stringify({
      reviewer_id: reviewerId,
      resolution_notes: "Resolved from operator console; no automation performed."
    }),
    headers: authHeaders(token),
    method: "POST"
  });
  return mapManualHandoff(payload);
}

export async function getDiscoveryQueueRuns(): Promise<DiscoveryQueueRun[]> {
  const payload = await request<ApiDiscoveryQueueRun[]>("/discovery-queue/runs?limit=20");
  return payload.map(mapDiscoveryRun);
}

export async function enqueueDiscoveryQueueRun(
  token: string,
  requestBody: DiscoveryQueueRunRequest
): Promise<DiscoveryQueueRun> {
  const payload = await request<ApiDiscoveryQueueRun>("/discovery-queue/runs", {
    body: JSON.stringify({
      url: requestBody.url,
      source_domain: requestBody.sourceDomain || undefined,
      mode: requestBody.mode,
      requested_by: requestBody.requestedBy,
      max_results: requestBody.maxResults,
      max_attempts: requestBody.maxAttempts ?? 3
    }),
    headers: authHeaders(token),
    method: "POST"
  });
  return mapDiscoveryRun(payload);
}

export async function processDiscoveryQueueRun(
  token: string,
  runId: string
): Promise<DiscoveryQueueRun> {
  const payload = await request<ApiDiscoveryQueueRun>(`/discovery-queue/runs/${runId}/process`, {
    headers: authHeaders(token),
    method: "POST"
  });
  return mapDiscoveryRun(payload);
}

export async function getObservabilitySummary(): Promise<ObservabilitySummary> {
  const payload = await request<ApiObservabilitySummary>("/observability/summary");
  return {
    totalAuditEvents: payload.total_audit_events,
    errorEvents: payload.error_events,
    openManualHandoffs: payload.open_manual_handoffs,
    queuedDiscoveryRuns: payload.queued_discovery_runs,
    failedDiscoveryRuns: payload.failed_discovery_runs,
    auditChainValid: payload.audit_chain_valid,
    latestAuditHash: payload.latest_audit_hash,
    activeAlerts: payload.active_alerts.map((alert) => ({
      id: alert.id,
      severity: alert.severity,
      title: alert.title,
      detail: alert.detail,
      recommendedAction: alert.recommended_action
    }))
  };
}

export async function getSourceRecords(): Promise<SourceRecord[]> {
  const payload = await request<ApiSourceRecord[]>("/sources");
  return payload.map((item) => ({
    id: item.id,
    name: item.name,
    domain: item.domain,
    sourceType: item.source_type,
    policyStatus: item.latest_policy?.status ?? null
  }));
}

export async function attachSourcePolicy(
  token: string,
  attachment: SourcePolicyAttachment
): Promise<void> {
  await request<unknown>("/source-policies", {
    body: JSON.stringify({
      source_id: attachment.sourceId,
      status: attachment.status,
      reason: attachment.reason,
      allowed_actions: attachment.allowedActions,
      denied_actions: attachment.deniedActions
    }),
    headers: authHeaders(token),
    method: "POST"
  });
}

async function request<T>(
  path: string,
  init: { body?: string; headers?: Record<string, string>; method?: string } = {}
): Promise<T> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
  if (!apiBaseUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured.");
  }
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: init.method ?? "GET",
    headers: { accept: "application/json", ...(init.headers ?? {}) },
    ...(init.body === undefined ? {} : { body: init.body })
  });
  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : response.statusText;
    throw new Error(`Operator API returned HTTP ${response.status}: ${detail}`);
  }
  return payload as T;
}

function authHeaders(token: string): Record<string, string> {
  return { authorization: `Bearer ${token}`, "content-type": "application/json" };
}

function mapManualHandoff(item: ApiManualHandoff): ManualHandoff {
  return {
    id: item.id,
    url: item.url,
    sourceDomain: item.source_domain,
    triggerType: item.trigger_type,
    requestedBy: item.requested_by,
    status: item.status,
    detectionDetail: item.detection_detail,
    runId: item.run_id,
    createdAt: item.created_at,
    resolvedAt: item.resolved_at
  };
}

function mapDiscoveryRun(item: ApiDiscoveryQueueRun): DiscoveryQueueRun {
  return {
    id: item.id,
    mode: item.mode,
    url: item.url,
    sourceDomain: item.source_domain,
    requestedBy: item.requested_by,
    status: item.status,
    attempts: item.attempts,
    maxAttempts: item.max_attempts,
    rateLimitAfter: item.rate_limit_after,
    liveRunId: item.live_run_id,
    manualHandoffId: item.manual_handoff_id,
    failureReason: item.failure_reason,
    discoveredUrls: item.discovered_urls,
    reviewItemIds: item.review_item_ids,
    createdAt: item.created_at
  };
}
