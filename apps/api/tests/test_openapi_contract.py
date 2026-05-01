from __future__ import annotations

import json
from pathlib import Path

from app.tools.openapi_contract import (
    DISALLOWED_ROUTE_FRAGMENTS,
    EXPECTED_PHASE_1_PATHS,
    build_openapi_contract,
    validate_openapi_contract,
    write_openapi_contract,
)


def test_openapi_contract_contains_phase_1_routes_without_unsafe_routes() -> None:
    contract = build_openapi_contract()
    paths = set(contract["paths"])

    assert paths >= EXPECTED_PHASE_1_PATHS
    assert validate_openapi_contract(contract) == []
    assert not [
        path
        for path in paths
        if any(fragment in path for fragment in DISALLOWED_ROUTE_FRAGMENTS)
    ]


def test_openapi_contract_can_be_written_as_stable_json(tmp_path: Path) -> None:
    output_path = tmp_path / "jobfinder-openapi.json"

    write_openapi_contract(output_path)

    payload = json.loads(output_path.read_text())
    assert payload["info"]["title"] == "Jobfinder API"
    assert payload["info"]["version"] == "0.1.0"
    assert "/source-policies/check" in payload["paths"]


def test_committed_openapi_artifact_matches_generated_contract() -> None:
    artifact_path = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "openapi"
        / "jobfinder-openapi.json"
    )

    committed_contract = json.loads(artifact_path.read_text())

    assert committed_contract == build_openapi_contract()
