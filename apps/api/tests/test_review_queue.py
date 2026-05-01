from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.adapters import RawJobPosting
from app.main import create_app
from app.schemas.review import ReviewQueueItem, ReviewQueueSummary
from app.services.review_queue import ReviewQueueService


def make_raw_job(**overrides: object) -> RawJobPosting:
    values: dict[str, object] = {
        "source": "greenhouse",
        "source_url": "https://jobs.example.com/acme/backend-engineer",
        "application_url": "https://jobs.example.com/acme/backend-engineer/apply",
        "external_id": "gh-1",
        "title": "Backend Engineer",
        "company": "Acme Robotics",
        "locations": ("London, UK",),
        "remote_type": "onsite",
        "employment_type": "full_time",
        "salary_min": 100000,
        "salary_max": 120000,
        "salary_currency": "USD",
        "posted_date": date(2026, 3, 1),
        "valid_through": None,
        "extraction_method": "official_api_fixture",
        "raw_payload_hash": "a" * 64,
    }
    values.update(overrides)
    return RawJobPosting(**values)


def test_review_queue_builds_ready_items_from_synthetic_adapter_fixtures() -> None:
    service = ReviewQueueService()

    items = service.list_items()
    summary = service.get_summary()

    assert len(items) == 7
    assert summary == ReviewQueueSummary(total=7, ready=7, needs_review=0)
    assert all(item.synthetic for item in items)
    assert all(item.data_origin == "synthetic_adapter_fixture" for item in items)
    assert {item.fixture_name for item in items} == {
        "ashby_remote.json",
        "greenhouse_missing_salary.json",
        "jsonld_remote.json",
        "lever_multiple_locations.json",
        "smartrecruiters_expired.json",
        "static_html_on_site.html",
        "workable_hybrid.json",
    }
    assert all(item.extraction_confidence == 1.0 for item in items)


def test_low_confidence_extraction_routes_to_review_queue() -> None:
    low_confidence_raw = make_raw_job().model_construct(
        **{**make_raw_job().model_dump(), "title": "", "locations": ()}
    )
    service = ReviewQueueService(raw_postings=(low_confidence_raw,), fixture_specs=())

    needs_review = service.list_items(status="needs_review")
    ready = service.list_items(status="ready")

    assert len(needs_review) == 1
    assert ready == []
    item = needs_review[0]
    assert item.review_status == "needs_review"
    assert item.extraction_confidence < 0.8
    assert "title is missing" in item.review_reasons
    assert item.locations == ("unknown",)
    assert item.provenance_hints["title"].confidence == 0.0
    assert item.provenance_hints["locations"].confidence < 0.8


def test_review_queue_can_filter_ready_items_and_count_mixed_statuses() -> None:
    ready_raw = make_raw_job(external_id="ready-1")
    low_confidence_raw = make_raw_job().model_construct(
        **{**make_raw_job(external_id="review-1").model_dump(), "company": ""}
    )
    service = ReviewQueueService(
        raw_postings=(ready_raw, low_confidence_raw),
        fixture_specs=(),
    )

    ready_items = service.list_items(status="ready")
    needs_review_items = service.list_items(status="needs_review")
    summary = service.get_summary()

    assert [item.external_id for item in ready_items] == ["ready-1"]
    assert [item.external_id for item in needs_review_items] == ["review-1"]
    assert summary.total == 2
    assert summary.ready == 1
    assert summary.needs_review == 1


def test_review_queue_endpoint_returns_typed_schema() -> None:
    client = TestClient(create_app())

    response = client.get("/review/queue")

    assert response.status_code == 200
    items = [ReviewQueueItem.model_validate(item) for item in response.json()]
    assert len(items) == 7
    assert all(item.synthetic for item in items)
    assert all(item.title for item in items)
    assert all("title" in item.provenance_hints for item in items)


def test_review_summary_endpoint_returns_typed_schema() -> None:
    client = TestClient(create_app())

    response = client.get("/review/summary")

    assert response.status_code == 200
    summary = ReviewQueueSummary.model_validate(response.json())
    assert summary.total == 7
    assert summary.ready == 7
    assert summary.needs_review == 0
