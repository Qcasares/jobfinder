from __future__ import annotations

from datetime import date

from app.adapters import RawJobPosting
from app.services.extraction import extract_job_posting

CANONICAL_FIELDS = {
    "source_url",
    "application_url",
    "title",
    "company",
    "locations",
    "remote_type",
    "salary_min",
    "salary_max",
    "salary_currency",
    "employment_type",
    "posted_date",
    "valid_through",
    "required_skills",
    "preferred_skills",
    "responsibilities",
    "qualifications",
    "extraction_confidence",
}


def make_raw_job(**overrides: object) -> RawJobPosting:
    values: dict[str, object] = {
        "source": "greenhouse",
        "source_url": "https://jobs.example.com/acme/backend-engineer",
        "application_url": "https://jobs.example.com/acme/backend-engineer/apply",
        "external_id": "gh-1",
        "title": "Backend Engineer",
        "company": "Acme Robotics",
        "locations": (" London, UK ",),
        "remote_type": "onsite",
        "employment_type": "full_time",
        "salary_min": 100000,
        "salary_max": 120000,
        "salary_currency": "usd",
        "posted_date": date(2026, 3, 1),
        "valid_through": None,
        "extraction_method": "official_api_fixture",
        "raw_payload_hash": "a" * 64,
    }
    values.update(overrides)
    return RawJobPosting(**values)


def test_extracts_valid_raw_job_with_structured_fields_and_provenance() -> None:
    raw = make_raw_job()

    extracted = extract_job_posting(
        raw,
        description_text="Build Python APIs with FastAPI and PostgreSQL.",
        responsibilities_text="Own backend services.",
        qualifications_text="Requires Python, SQL, and FastAPI.",
    )

    assert extracted.source_url == raw.source_url
    assert extracted.application_url == raw.application_url
    assert extracted.title == "Backend Engineer"
    assert extracted.company == "Acme Robotics"
    assert extracted.locations == ("London, UK",)
    assert extracted.remote_type == "onsite"
    assert extracted.salary_min == 100000
    assert extracted.salary_max == 120000
    assert extracted.salary_currency == "USD"
    assert extracted.employment_type == "full_time"
    assert extracted.posted_date == date(2026, 3, 1)
    assert extracted.responsibilities == "Own backend services."
    assert extracted.qualifications == "Requires Python, SQL, and FastAPI."
    assert extracted.required_skills == ("FastAPI", "Python", "SQL")
    assert extracted.preferred_skills == ()
    assert extracted.requires_review is False
    assert extracted.extraction_confidence >= 0.9
    assert set(extracted.field_provenance) == CANONICAL_FIELDS
    assert extracted.field_provenance["title"].confidence == 1.0


def test_missing_salary_is_preserved_as_none_without_review() -> None:
    raw = make_raw_job(salary_min=None, salary_max=None, salary_currency=None)

    extracted = extract_job_posting(raw)

    assert extracted.salary_min is None
    assert extracted.salary_max is None
    assert extracted.salary_currency is None
    assert extracted.requires_review is False
    assert extracted.field_provenance["salary_min"].confidence == 1.0
    assert "missing" in extracted.field_provenance["salary_min"].note


def test_reversed_salary_range_is_swapped_with_low_confidence_note() -> None:
    raw = make_raw_job().model_construct(
        **{
            **make_raw_job().model_dump(),
            "salary_min": 150000,
            "salary_max": 90000,
            "salary_currency": "USD",
        }
    )

    extracted = extract_job_posting(raw)

    assert extracted.salary_min == 90000
    assert extracted.salary_max == 150000
    assert extracted.requires_review is True
    assert extracted.review_status == "needs_review"
    assert extracted.field_provenance["salary_min"].confidence < 0.8
    assert "reversed" in extracted.field_provenance["salary_min"].note
    assert "salary range was reversed" in extracted.review_reasons


def test_multiple_locations_are_trimmed_and_deduped() -> None:
    raw = make_raw_job(locations=(" London, UK ", "Remote - UK", "london, uk", ""))

    extracted = extract_job_posting(raw)

    assert extracted.locations == ("London, UK", "Remote - UK")


def test_empty_locations_are_classified_as_unknown() -> None:
    raw = make_raw_job().model_construct(**{**make_raw_job().model_dump(), "locations": ()})

    extracted = extract_job_posting(raw)

    assert extracted.locations == ("unknown",)
    assert extracted.field_provenance["locations"].confidence < 0.8


def test_remote_type_classification_uses_raw_value_and_location_text() -> None:
    assert extract_job_posting(make_raw_job(remote_type="remote")).remote_type == "remote"
    assert (
        extract_job_posting(make_raw_job(remote_type=None, locations=("Hybrid - New York",)))
        .remote_type
        == "hybrid"
    )
    assert (
        extract_job_posting(make_raw_job(remote_type=None, locations=("Austin, TX",))).remote_type
        == "onsite"
    )
    assert (
        extract_job_posting(make_raw_job(remote_type=None, locations=("North America",)))
        .remote_type
        == "unknown"
    )


def test_skill_extraction_is_deterministic_from_text_fields_only() -> None:
    raw = make_raw_job(title="Backend Engineer", company="Acme Robotics")

    extracted = extract_job_posting(
        raw,
        description_text="Nice to have React. This role partners with data science teams.",
        responsibilities_text="Build APIs in Python and PostgreSQL.",
        qualifications_text="Must have Python, SQL, Docker, and Kubernetes experience.",
    )

    assert extracted.required_skills == ("Docker", "Kubernetes", "PostgreSQL", "Python", "SQL")
    assert extracted.preferred_skills == ("Data Science", "React")
    assert extracted.field_provenance["required_skills"].source == "text_fields"
    assert extracted.field_provenance["preferred_skills"].source == "text_fields"


def test_missing_required_fields_route_to_review() -> None:
    raw = make_raw_job().model_construct(**{**make_raw_job().model_dump(), "title": ""})

    extracted = extract_job_posting(raw)

    assert extracted.requires_review is True
    assert extracted.review_status == "needs_review"
    assert "title is missing" in extracted.review_reasons
    assert extracted.extraction_confidence < 0.8
