from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.main import create_app

OpenApiDocument = dict[str, Any]

EXPECTED_PHASE_1_PATHS = {
    "/applications",
    "/applications/summary",
    "/approvals/requests",
    "/approvals/requests/{request_id}/decision",
    "/approvals/summary",
    "/auth/operator-token",
    "/autofill/packets",
    "/audit/events",
    "/audit/summary",
    "/audit/verify-chain",
    "/candidate/evidence",
    "/candidate/document-records",
    "/candidate/document-records/export",
    "/candidate/document-records/{record_id}",
    "/candidate/profile",
    "/candidate/search-criteria",
    "/candidate/workspace",
    "/dashboard/summary",
    "/discovery-queue/runs",
    "/discovery-queue/runs/{run_id}/process",
    "/drafting/runs",
    "/final-review/packets",
    "/health",
    "/jobs",
    "/jobs/summary",
    "/live-discovery/runs",
    "/live-discovery/runs/{run_id}",
    "/live-discovery/search-runs",
    "/live-discovery/search-runs/{run_id}",
    "/maintenance/migrations/upgrade",
    "/manual-handoffs",
    "/manual-handoffs/{record_id}/resolve",
    "/observability/summary",
    "/review/queue",
    "/review/summary",
    "/settings/runtime",
    "/source-policies",
    "/source-policies/check",
    "/source-policies/seed-known",
    "/sources",
}

DISALLOWED_ROUTE_FRAGMENTS = {
    "assisted-apply",
    "crawl",
    "handoff-packet",
    "llm",
    "submit",
}


def build_openapi_contract() -> OpenApiDocument:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            redis_url="",
            service_name="jobfinder-api",
            environment="contract",
        )
    )
    return app.openapi()


def validate_openapi_contract(contract: OpenApiDocument) -> list[str]:
    paths = set(contract.get("paths", {}))
    errors: list[str] = []
    missing_paths = sorted(EXPECTED_PHASE_1_PATHS - paths)

    if missing_paths:
        errors.append(f"missing expected paths: {', '.join(missing_paths)}")

    unsafe_paths = sorted(
        path
        for path in paths
        if any(fragment in path.casefold() for fragment in DISALLOWED_ROUTE_FRAGMENTS)
    )
    if unsafe_paths:
        errors.append(f"unsafe route paths present: {', '.join(unsafe_paths)}")

    return errors


def write_openapi_contract(output_path: Path) -> None:
    contract = build_openapi_contract()
    errors = validate_openapi_contract(contract)
    if errors:
        raise RuntimeError("; ".join(errors))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{json.dumps(contract, indent=2, sort_keys=True)}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate or export the Jobfinder OpenAPI contract."
    )
    parser.add_argument("--check", action="store_true", help="Validate without writing a file.")
    parser.add_argument("--output", type=Path, help="Optional output JSON path.")
    args = parser.parse_args()

    contract = build_openapi_contract()
    errors = validate_openapi_contract(contract)
    if errors:
        for error in errors:
            print(error)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{json.dumps(contract, indent=2, sort_keys=True)}\n")
    elif not args.check:
        print(json.dumps(contract, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
