from datetime import date

import pytest

from app.adapters import (
    AshbyAdapter,
    GreenhouseAdapter,
    JsonLdAdapter,
    LeverAdapter,
    RawJobPosting,
    SmartRecruitersAdapter,
    StaticHtmlAdapter,
    WorkableAdapter,
    dedupe_raw_job_postings,
    load_adapter_fixture,
)


@pytest.mark.parametrize(
    ("fixture_name", "adapter", "expected_source", "expected_title"),
    [
        (
            "greenhouse_missing_salary.json",
            GreenhouseAdapter(),
            "greenhouse",
            "Backend Engineer",
        ),
        ("lever_multiple_locations.json", LeverAdapter(), "lever", "Platform Engineer"),
        ("ashby_remote.json", AshbyAdapter(), "ashby", "ML Infrastructure Engineer"),
        (
            "smartrecruiters_expired.json",
            SmartRecruitersAdapter(),
            "smartrecruiters",
            "Data Analyst",
        ),
        ("workable_hybrid.json", WorkableAdapter(), "workable", "Customer Success Manager"),
        ("jsonld_remote.json", JsonLdAdapter(), "json-ld", "Security Engineer"),
        ("static_html_on_site.html", StaticHtmlAdapter(), "static-html", "Facilities Coordinator"),
    ],
)
def test_each_adapter_parses_synthetic_fixture(
    fixture_name: str,
    adapter: GreenhouseAdapter
    | LeverAdapter
    | AshbyAdapter
    | SmartRecruitersAdapter
    | WorkableAdapter
    | JsonLdAdapter
    | StaticHtmlAdapter,
    expected_source: str,
    expected_title: str,
) -> None:
    payload = load_adapter_fixture(fixture_name)

    jobs = adapter.parse(payload, source_url=f"https://fixtures.local/{fixture_name}")

    assert len(jobs) == 1
    job = jobs[0]
    assert isinstance(job, RawJobPosting)
    assert job.source == expected_source
    assert job.title == expected_title
    assert job.source_url
    assert job.application_url
    assert job.external_id
    assert job.company
    assert job.locations
    assert job.extraction_method == adapter.extraction_method
    assert len(job.raw_payload_hash) == 64


def test_fixture_loader_reads_text_and_blocks_path_traversal() -> None:
    payload = load_adapter_fixture("static_html_on_site.html")

    assert "Facilities Coordinator" in payload
    with pytest.raises(ValueError):
        load_adapter_fixture("../source-policies/README.md")


def test_greenhouse_adapter_preserves_missing_salary_as_none() -> None:
    jobs = GreenhouseAdapter().parse(
        load_adapter_fixture("greenhouse_missing_salary.json"),
        source_url="https://fixtures.local/greenhouse",
    )

    assert jobs[0].salary_min is None
    assert jobs[0].salary_max is None
    assert jobs[0].salary_currency is None


def test_lever_adapter_emits_multiple_locations() -> None:
    jobs = LeverAdapter().parse(
        load_adapter_fixture("lever_multiple_locations.json"),
        source_url="https://fixtures.local/lever",
    )

    assert jobs[0].locations == ("New York, NY", "Remote - US")


def test_ashby_adapter_maps_remote_job() -> None:
    jobs = AshbyAdapter().parse(
        load_adapter_fixture("ashby_remote.json"),
        source_url="https://fixtures.local/ashby",
    )

    assert jobs[0].remote_type == "remote"
    assert jobs[0].locations == ("Remote - Canada",)


def test_smartrecruiters_adapter_keeps_expired_valid_through_date() -> None:
    jobs = SmartRecruitersAdapter().parse(
        load_adapter_fixture("smartrecruiters_expired.json"),
        source_url="https://fixtures.local/smartrecruiters",
    )

    assert jobs[0].valid_through == date(2026, 1, 1)


def test_dedupe_prefers_canonical_urls_then_normalized_signatures() -> None:
    first = RawJobPosting(
        source="greenhouse",
        source_url="https://jobs.example.com/acme/backend-engineer?utm_source=test",
        application_url="https://jobs.example.com/acme/backend-engineer/apply",
        external_id="gh-1",
        title="Backend Engineer",
        company="Acme Robotics",
        locations=("London, UK",),
        remote_type="onsite",
        employment_type="full_time",
        salary_min=100000,
        salary_max=120000,
        salary_currency="USD",
        posted_date=date(2026, 3, 1),
        valid_through=None,
        extraction_method="official_api_fixture",
        raw_payload_hash="a" * 64,
    )
    duplicate_url = first.model_copy(update={"external_id": "gh-duplicate"})
    duplicate_signature = first.model_copy(
        update={
            "source": "lever",
            "source_url": "https://lever.example.com/acme/platform",
            "application_url": "https://lever.example.com/acme/platform/apply",
            "external_id": "lever-1",
            "title": " backend engineer ",
            "company": "ACME Robotics",
            "locations": ("London, UK",),
            "raw_payload_hash": "b" * 64,
        }
    )
    unique = first.model_copy(
        update={
            "source_url": "https://jobs.example.com/acme/frontend-engineer",
            "application_url": "https://jobs.example.com/acme/frontend-engineer/apply",
            "external_id": "gh-2",
            "title": "Frontend Engineer",
            "raw_payload_hash": "c" * 64,
        }
    )

    deduped = dedupe_raw_job_postings([first, duplicate_url, duplicate_signature, unique])

    assert [job.external_id for job in deduped] == ["gh-1", "gh-2"]
