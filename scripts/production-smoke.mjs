#!/usr/bin/env node

const DEFAULT_WEB_URL = "https://jobfinder.quentincasares.com";
const DEFAULT_API_BASE_URL = "https://api.jobfinder.quentincasares.com";

const webUrl = (process.env.JOBFINDER_WEB_URL || DEFAULT_WEB_URL).replace(/\/$/, "");
const apiBaseUrl = (process.env.JOBFINDER_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");

const checks = [];

await checkWeb();
await checkHealth();
await checkRuntime();
await checkCors();
await checkUnauthenticatedMutationDeny();

console.log(JSON.stringify({ ok: true, checks }, null, 2));

async function checkWeb() {
  const response = await fetch(`${webUrl}/`, { redirect: "manual" });
  assert(response.ok, `Web returned HTTP ${response.status}`);
  const html = await response.text();
  assert(html.includes("Jobfinder Operations"), "Web HTML is missing the app title.");
  assert(html.includes("Live discovery"), "Web HTML is missing runtime capability content.");
  assert(html.includes("Operator API key"), "Web HTML is missing operator capability content.");
  checks.push({ name: "web", status: response.status });
}

async function checkHealth() {
  const payload = await getJson(`${apiBaseUrl}/health`);
  assert(payload.status === "ok", "API health status is not ok.");
  assert(payload.service === "jobfinder-api", "API health service is unexpected.");
  checks.push({ name: "api_health", service: payload.service });
}

async function checkRuntime() {
  const payload = await getJson(`${apiBaseUrl}/settings/runtime`);
  const capabilities = Object.fromEntries(
    payload.capabilities.map((capability) => [capability.key, capability.enabled])
  );
  const expectedEnabled = [
    "operator_api_key",
    "operator_session_auth",
    "write_api",
    "live_discovery",
    "live_search_discovery",
    "manual_handoff",
    "candidate_vault",
    "autofill_packets",
    "submission_packets"
  ];
  const expectedDisabled = ["llm_drafting", "browser_automation", "autofill_submit"];

  assert(payload.environment === "production", "Runtime environment is not production.");
  assert(payload.database_configured === true, "Runtime database is not configured.");
  assert(payload.secrets_loaded === true, "Runtime operator secret is not configured.");

  for (const key of expectedEnabled) {
    assert(capabilities[key] === true, `Runtime capability ${key} is not enabled.`);
  }
  for (const key of expectedDisabled) {
    assert(capabilities[key] === false, `Runtime capability ${key} is unexpectedly enabled.`);
  }

  checks.push({ name: "runtime", environment: payload.environment });
}

async function checkCors() {
  const response = await fetch(`${apiBaseUrl}/live-discovery/runs`, {
    method: "OPTIONS",
    headers: {
      origin: webUrl,
      "access-control-request-method": "POST",
      "access-control-request-headers": "authorization,content-type,x-jobfinder-operator-key"
    }
  });
  const allowedOrigin = response.headers.get("access-control-allow-origin");
  const allowedHeaders = response.headers.get("access-control-allow-headers") || "";

  assert(response.ok, `CORS preflight returned HTTP ${response.status}`);
  assert(allowedOrigin === webUrl, "CORS preflight did not echo the production web origin.");
  assert(
    allowedHeaders.toLowerCase().includes("x-jobfinder-operator-key"),
    "CORS preflight does not allow the operator header."
  );
  assert(
    allowedHeaders.toLowerCase().includes("authorization"),
    "CORS preflight does not allow the authorization header."
  );
  checks.push({ name: "cors", status: response.status });
}

async function checkUnauthenticatedMutationDeny() {
  const response = await fetch(`${apiBaseUrl}/live-discovery/runs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ url: "https://unknown.example.test/jobs/platform" })
  });
  const payload = await response.json();

  assert(response.status === 401, `Unauthenticated mutation returned HTTP ${response.status}.`);
  assert(
    payload.detail === "A valid operator API key is required.",
    "Unauthenticated mutation denial detail changed."
  );
  checks.push({ name: "unauthenticated_mutation_denied", status: response.status });

  const handoffResponse = await fetch(`${apiBaseUrl}/manual-handoffs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      url: "https://unknown.example.test/jobs/platform",
      trigger_type: "login_required",
      requested_by: "production-smoke",
      detection_detail: "Manual handoff smoke probe."
    })
  });
  assert(
    handoffResponse.status === 401,
    `Unauthenticated handoff mutation returned HTTP ${handoffResponse.status}.`
  );
  checks.push({ name: "unauthenticated_handoff_mutation_denied", status: handoffResponse.status });
}

async function getJson(url) {
  const response = await fetch(url, { headers: { accept: "application/json" } });
  assert(response.ok, `${url} returned HTTP ${response.status}`);
  return response.json();
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}
