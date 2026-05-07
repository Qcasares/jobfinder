export type SettingsDataSource = "api" | "local";
export type RuntimeCapabilityKey =
  | "source_policy_gate"
  | "audit_hash_chain"
  | "single_user_local_mode"
  | "live_crawling"
  | "live_discovery"
  | "live_search_discovery"
  | "llm_calls"
  | "llm_drafting"
  | "browser_automation"
  | "autofill_packets"
  | "submission_packets"
  | "autofill_submit"
  | "candidate_vault"
  | "real_candidate_data";

export type RuntimeCapability = {
  key: RuntimeCapabilityKey;
  label: string;
  enabled: boolean;
  detail: string;
};

export type RuntimeSettings = {
  serviceName: string;
  environment: string;
  auditSchemaVersion: number;
  databaseConfigured: boolean;
  redisConfigured: boolean;
  secretsLoaded: boolean;
  externalIntegrationsEnabled: boolean;
  capabilities: RuntimeCapability[];
};

export type SettingsSnapshot = {
  source: SettingsDataSource;
  detail: string;
  checkedUrl?: string;
  runtime: RuntimeSettings;
};

type ApiRuntimeSettings = {
  service_name: string;
  environment: string;
  audit_schema_version: number;
  database_configured: boolean;
  redis_configured: boolean;
  secrets_loaded: boolean;
  external_integrations_enabled: boolean;
  capabilities: RuntimeCapability[];
};

export async function getSettingsSnapshot(): Promise<SettingsSnapshot> {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!apiBaseUrl) {
    return localSettingsSnapshot(
      "NEXT_PUBLIC_API_BASE_URL is not configured; safe local runtime posture is shown."
    );
  }

  const runtimeUrl = new URL("/settings/runtime", apiBaseUrl).toString();

  try {
    const response = await fetch(runtimeUrl, {
      cache: "no-store",
      headers: { accept: "application/json" }
    });

    if (!response.ok) {
      return localSettingsSnapshot(
        `Settings API returned HTTP ${response.status}; safe local runtime posture is shown.`,
        runtimeUrl
      );
    }

    const runtime = mapApiRuntimeSettings((await response.json()) as ApiRuntimeSettings);
    return {
      source: "api",
      detail: "Runtime settings expose safe posture metadata only; secrets and connection URLs are not returned.",
      checkedUrl: runtimeUrl,
      runtime
    };
  } catch {
    return localSettingsSnapshot(
      "Settings API is unreachable; safe local runtime posture is shown.",
      runtimeUrl
    );
  }
}

function mapApiRuntimeSettings(settings: ApiRuntimeSettings): RuntimeSettings {
  return {
    serviceName: settings.service_name,
    environment: settings.environment,
    auditSchemaVersion: settings.audit_schema_version,
    databaseConfigured: settings.database_configured,
    redisConfigured: settings.redis_configured,
    secretsLoaded: settings.secrets_loaded,
    externalIntegrationsEnabled: settings.external_integrations_enabled,
    capabilities: settings.capabilities
  };
}

function localSettingsSnapshot(detail: string, checkedUrl?: string): SettingsSnapshot {
  return {
    source: "local",
    detail,
    checkedUrl,
    runtime: {
      serviceName: "jobfinder-api",
      environment: "local",
      auditSchemaVersion: 1,
      databaseConfigured: false,
      redisConfigured: false,
      secretsLoaded: false,
      externalIntegrationsEnabled: false,
      capabilities: [
        {
          key: "source_policy_gate",
          label: "Source policy gate",
          enabled: true,
          detail: "Unknown and prohibited sources are denied by default."
        },
        {
          key: "audit_hash_chain",
          label: "Hash-chained audit log",
          enabled: true,
          detail: "Material decisions are recorded with previous and current hashes."
        },
        {
          key: "single_user_local_mode",
          label: "Single-user local mode",
          enabled: true,
          detail: "Local owner fields are present, but no external auth provider is active."
        },
        {
          key: "live_crawling",
          label: "Live crawling",
          enabled: false,
          detail: "Disabled; broad unbounded crawling is not part of the live intake tranche."
        },
        {
          key: "live_discovery",
          label: "Live discovery",
          enabled: false,
          detail: "Disabled by default; enable only with source policy and audit gates."
        },
        {
          key: "live_search_discovery",
          label: "Live search discovery",
          enabled: false,
          detail: "Disabled by default; enable only after crawl budgets and policies."
        },
        {
          key: "llm_calls",
          label: "LLM calls",
          enabled: false,
          detail: "Disabled by default; no model provider is invoked."
        },
        {
          key: "llm_drafting",
          label: "LLM-assisted drafting",
          enabled: false,
          detail: "Disabled by default; drafting requires explicit runtime opt-in."
        },
        {
          key: "browser_automation",
          label: "Browser automation",
          enabled: false,
          detail:
            "Disabled; autofill packets are dry-run review artifacts and do not invoke a browser agent."
        },
        {
          key: "autofill_packets",
          label: "Autofill packets",
          enabled: false,
          detail: "Disabled by default; packet preparation requires explicit opt-in."
        },
        {
          key: "submission_packets",
          label: "Final review packets",
          enabled: false,
          detail: "Disabled by default; final review packet preparation requires explicit opt-in."
        },
        {
          key: "autofill_submit",
          label: "Autofill and submit",
          enabled: false,
          detail:
            "Disabled; autofill packets are dry-run review artifacts and external submission remains blocked."
        },
        {
          key: "candidate_vault",
          label: "Candidate vault",
          enabled: false,
          detail: "Disabled by default; real candidate document records require explicit vault enablement."
        },
        {
          key: "real_candidate_data",
          label: "Real candidate data",
          enabled: false,
          detail:
            "Disabled for profile/evidence text; candidate vault records may only reference external encrypted storage metadata when separately enabled."
        }
      ]
    }
  };
}
