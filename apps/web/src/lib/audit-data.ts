import { dashboardData } from "./dashboard-data";

export type AuditDataSource = "api" | "local";
export type AuditActorType = "user" | "system" | "worker";

export type AuditEventItem = {
  id: string;
  eventType: string;
  actorType: AuditActorType;
  actorId: string;
  correlationId: string;
  schemaVersion: number;
  previousHash: string | null;
  eventHash: string;
  payload: Record<string, unknown>;
  createdAt: string;
};

export type AuditSummary = {
  total: number;
  chainValid: boolean;
  latestHash: string | null;
  latestEventAt: string | null;
};

export type AuditSnapshot = {
  source: AuditDataSource;
  detail: string;
  checkedUrl?: string;
  summary: AuditSummary;
  events: AuditEventItem[];
};

type ApiAuditSummary = {
  total_events: number;
  counts_by_event_type: Record<string, number>;
  counts_by_actor_type: Record<string, number>;
  latest_hash: string | null;
  chain: {
    valid: boolean;
    event_count: number;
    latest_hash: string | null;
    invalid_event_id: string | null;
    reason: string;
  };
};

type ApiAuditEvent = {
  id: string;
  event_type: string;
  actor_type: AuditActorType;
  actor_id: string;
  correlation_id: string;
  schema_version: number;
  previous_hash: string | null;
  event_hash: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export async function getAuditSnapshot(): Promise<AuditSnapshot> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return localAuditSnapshot(
      "NEXT_PUBLIC_API_BASE_URL is not configured; local audit fallback data is shown."
    );
  }

  const summaryUrl = new URL("/audit/summary", apiBaseUrl).toString();
  const eventsUrl = new URL("/audit/events?limit=25", apiBaseUrl).toString();

  try {
    const [summaryResponse, eventsResponse] = await Promise.all([
      fetch(summaryUrl, { cache: "no-store", headers: { accept: "application/json" } }),
      fetch(eventsUrl, { cache: "no-store", headers: { accept: "application/json" } })
    ]);

    if (!summaryResponse.ok || !eventsResponse.ok) {
      return localAuditSnapshot(
        `Audit API returned HTTP ${summaryResponse.status}/${eventsResponse.status}; local audit fallback data is shown.`,
        eventsUrl
      );
    }

    const summary = (await summaryResponse.json()) as ApiAuditSummary;
    const events = ((await eventsResponse.json()) as ApiAuditEvent[]).map(mapApiAuditEvent);

    return {
      source: "api",
      detail: "Audit events are loaded from the FastAPI hash-chained audit log.",
      checkedUrl: eventsUrl,
      summary: {
        total: summary.total_events,
        chainValid: summary.chain.valid,
        latestHash: summary.latest_hash ?? summary.chain.latest_hash,
        latestEventAt: events.at(-1)?.createdAt ?? null
      },
      events
    };
  } catch {
    return localAuditSnapshot("Audit API is unreachable; local audit fallback data is shown.", eventsUrl);
  }
}

function mapApiAuditEvent(event: ApiAuditEvent): AuditEventItem {
  return {
    id: event.id,
    eventType: event.event_type,
    actorType: event.actor_type,
    actorId: event.actor_id,
    correlationId: event.correlation_id,
    schemaVersion: event.schema_version,
    previousHash: event.previous_hash,
    eventHash: event.event_hash,
    payload: event.payload,
    createdAt: event.created_at
  };
}

function localAuditSnapshot(detail: string, checkedUrl?: string): AuditSnapshot {
  const events = dashboardData.auditFeed.map((event, index): AuditEventItem => {
    const eventHash = `local-${event.id}`;
    const previousHash =
      index < dashboardData.auditFeed.length - 1
        ? `local-${dashboardData.auditFeed[index + 1].id}`
        : null;

    return {
      id: event.id,
      eventType: event.action.toLowerCase().replaceAll(" ", "."),
      actorType: event.actor === "reviewer" ? "user" : event.actor === "policy" ? "system" : "system",
      actorId: event.actor,
      correlationId: event.subject,
      schemaVersion: 1,
      previousHash,
      eventHash,
      payload: {
        subject: event.subject,
        provenance: event.provenance,
        origin: "local_fallback"
      },
      createdAt: `2026-04-30T${event.occurredAt}:00Z`
    };
  });

  return {
    source: "local",
    detail,
    checkedUrl,
    summary: {
      total: events.length,
      chainValid: true,
      latestHash: events[0]?.eventHash ?? null,
      latestEventAt: events[0]?.createdAt ?? null
    },
    events
  };
}
