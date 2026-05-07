#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const DEFAULT_API_BASE_URL = "https://api.jobfinder.quentincasares.com";
const OPERATOR_ENV_FILE = "apps/api/.env.operator.local";

const args = parseArgs(process.argv.slice(2));

if (args.help || !args.url) {
  printHelp();
  process.exit(args.help ? 0 : 2);
}

const apiBaseUrl = (args.apiBaseUrl || process.env.JOBFINDER_API_BASE_URL || DEFAULT_API_BASE_URL)
  .trim()
  .replace(/\/$/, "");
const operatorKey = await getOperatorKey();
const endpoint = args.search ? "/live-discovery/search-runs" : "/live-discovery/runs";
const body = {
  url: args.url,
  source_domain: args.sourceDomain || undefined,
  requested_by: args.requestedBy || "local-operator",
  ...(args.search ? { max_results: args.maxResults ?? 10 } : {})
};

const response = await fetch(`${apiBaseUrl}${endpoint}`, {
  method: "POST",
  headers: {
    accept: "application/json",
    "content-type": "application/json",
    "x-jobfinder-operator-key": operatorKey
  },
  body: JSON.stringify(body)
});

const payload = await response.json().catch(() => null);

if (!response.ok) {
  const detail = payload && typeof payload.detail === "string" ? payload.detail : response.statusText;
  console.error(`Live intake failed with HTTP ${response.status}: ${detail}`);
  process.exit(1);
}

if (args.json) {
  console.log(JSON.stringify(payload, null, 2));
} else {
  printSummary(payload);
}

function parseArgs(rawArgs) {
  const inputArgs = rawArgs[0] === "--" ? rawArgs.slice(1) : rawArgs;
  const parsed = {
    apiBaseUrl: "",
    help: false,
    json: false,
    maxResults: undefined,
    requestedBy: "",
    search: false,
    sourceDomain: "",
    url: ""
  };

  for (let index = 0; index < inputArgs.length; index += 1) {
    const arg = inputArgs[index];
    const next = inputArgs[index + 1];

    if (arg === "--help" || arg === "-h") {
      parsed.help = true;
    } else if (arg === "--json") {
      parsed.json = true;
    } else if (arg === "--search") {
      parsed.search = true;
    } else if (arg === "--url" && next) {
      parsed.url = next;
      index += 1;
    } else if (arg === "--source-domain" && next) {
      parsed.sourceDomain = next;
      index += 1;
    } else if (arg === "--requested-by" && next) {
      parsed.requestedBy = next;
      index += 1;
    } else if (arg === "--max-results" && next) {
      parsed.maxResults = Number(next);
      index += 1;
    } else if (arg === "--api-base-url" && next) {
      parsed.apiBaseUrl = next;
      index += 1;
    } else {
      throw new Error(`Unknown or incomplete argument: ${arg}`);
    }
  }

  if (parsed.maxResults !== undefined && !Number.isInteger(parsed.maxResults)) {
    throw new Error("--max-results must be an integer.");
  }

  return parsed;
}

async function getOperatorKey() {
  if (process.env.JOBFINDER_API_OPERATOR_API_KEY) {
    return process.env.JOBFINDER_API_OPERATOR_API_KEY;
  }

  const envPath = resolve(process.cwd(), OPERATOR_ENV_FILE);
  const contents = await readFile(envPath, "utf8").catch(() => "");
  const keyLine = contents
    .split(/\r?\n/)
    .find((line) => line.startsWith("JOBFINDER_API_OPERATOR_API_KEY="));
  const key = keyLine?.split("=", 2)[1]?.trim() ?? "";

  if (!key) {
    throw new Error(
      `Missing JOBFINDER_API_OPERATOR_API_KEY. Set it in the environment or ${OPERATOR_ENV_FILE}.`
    );
  }

  return key;
}

function printSummary(payload) {
  console.log(`Run ${payload.id}`);
  console.log(`Status: ${payload.status}`);
  console.log(`Source: ${payload.source_domain}`);
  console.log(`URL: ${payload.url}`);
  console.log(`Extracted: ${payload.extracted_count ?? 0}`);
  console.log(`Discovered: ${payload.discovered_count ?? 0}`);

  if (payload.failure) {
    console.log(`Failure: ${payload.failure.reason} - ${payload.failure.detail}`);
  }

  if (Array.isArray(payload.discovered_urls) && payload.discovered_urls.length > 0) {
    console.log("Discovered URLs:");
    for (const url of payload.discovered_urls) {
      console.log(`- ${url}`);
    }
  }
}

function printHelp() {
  console.log(`Usage:
  pnpm operator:live-intake -- --url <https-url> [--source-domain <domain>]
  pnpm operator:live-intake -- --search --url <https-search-url> [--max-results 10]

Options:
  --url <url>                HTTPS job or search page URL.
  --source-domain <domain>   Optional source domain override.
  --search                   Use search-result discovery instead of single-page extraction.
  --max-results <number>     Search-result budget, default 10.
  --requested-by <name>      Audit actor label, default local-operator.
  --api-base-url <url>       API base URL, default ${DEFAULT_API_BASE_URL}.
  --json                     Print raw JSON response.
`);
}
