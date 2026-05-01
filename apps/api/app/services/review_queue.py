from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.adapters import (
    AshbyAdapter,
    GreenhouseAdapter,
    JobSourceAdapter,
    JsonLdAdapter,
    LeverAdapter,
    RawJobPosting,
    SmartRecruitersAdapter,
    StaticHtmlAdapter,
    WorkableAdapter,
    load_adapter_fixture,
)
from app.schemas.extraction import ExtractedJobPosting, FieldProvenance
from app.schemas.review import (
    ReviewProvenanceHint,
    ReviewQueueItem,
    ReviewQueueStatusFilter,
    ReviewQueueSummary,
)
from app.services.extraction import extract_job_posting


@dataclass(frozen=True)
class ReviewFixtureSpec:
    fixture_name: str
    adapter: JobSourceAdapter


DEFAULT_REVIEW_FIXTURES: tuple[ReviewFixtureSpec, ...] = (
    ReviewFixtureSpec("greenhouse_missing_salary.json", GreenhouseAdapter()),
    ReviewFixtureSpec("lever_multiple_locations.json", LeverAdapter()),
    ReviewFixtureSpec("ashby_remote.json", AshbyAdapter()),
    ReviewFixtureSpec("smartrecruiters_expired.json", SmartRecruitersAdapter()),
    ReviewFixtureSpec("workable_hybrid.json", WorkableAdapter()),
    ReviewFixtureSpec("jsonld_remote.json", JsonLdAdapter()),
    ReviewFixtureSpec("static_html_on_site.html", StaticHtmlAdapter()),
)


class ReviewQueueService:
    def __init__(
        self,
        *,
        fixture_specs: Sequence[ReviewFixtureSpec] | None = None,
        raw_postings: Sequence[RawJobPosting] | None = None,
    ) -> None:
        self._fixture_specs = (
            DEFAULT_REVIEW_FIXTURES if fixture_specs is None else tuple(fixture_specs)
        )
        self._raw_postings = tuple(raw_postings or ())

    def list_items(self, status: ReviewQueueStatusFilter = "all") -> list[ReviewQueueItem]:
        items = [*self._items_from_fixtures(), *self._items_from_raw_postings()]
        if status == "all":
            return items
        return [item for item in items if item.review_status == status]

    def get_summary(self) -> ReviewQueueSummary:
        items = self.list_items()
        ready = sum(1 for item in items if item.review_status == "ready")
        needs_review = sum(1 for item in items if item.review_status == "needs_review")
        return ReviewQueueSummary(total=len(items), ready=ready, needs_review=needs_review)

    def _items_from_fixtures(self) -> list[ReviewQueueItem]:
        items: list[ReviewQueueItem] = []
        for spec in self._fixture_specs:
            payload = load_adapter_fixture(spec.fixture_name)
            raw_jobs = spec.adapter.parse(
                payload,
                source_url=f"https://fixtures.local/{spec.fixture_name}",
            )
            items.extend(
                self._item_from_raw(
                    raw,
                    data_origin="synthetic_adapter_fixture",
                    fixture_name=spec.fixture_name,
                )
                for raw in raw_jobs
            )
        return items

    def _items_from_raw_postings(self) -> list[ReviewQueueItem]:
        return [
            self._item_from_raw(
                raw,
                data_origin="synthetic_raw_posting",
                fixture_name=None,
            )
            for raw in self._raw_postings
        ]

    @staticmethod
    def _item_from_raw(
        raw: RawJobPosting,
        *,
        data_origin: str,
        fixture_name: str | None,
    ) -> ReviewQueueItem:
        extracted = extract_job_posting(raw)
        return ReviewQueueItem(
            id=f"{raw.source}:{raw.external_id}",
            source=raw.source,
            external_id=raw.external_id,
            source_url=extracted.source_url,
            application_url=extracted.application_url,
            title=extracted.title,
            company=extracted.company,
            locations=extracted.locations,
            remote_type=extracted.remote_type,
            salary_min=extracted.salary_min,
            salary_max=extracted.salary_max,
            salary_currency=extracted.salary_currency,
            employment_type=extracted.employment_type,
            posted_date=extracted.posted_date,
            valid_through=extracted.valid_through,
            required_skills=extracted.required_skills,
            preferred_skills=extracted.preferred_skills,
            review_status=extracted.review_status,
            review_reasons=extracted.review_reasons,
            extraction_confidence=extracted.extraction_confidence,
            provenance_hints=_provenance_hints(extracted),
            synthetic=True,
            data_origin=data_origin,
            fixture_name=fixture_name,
        )


def _provenance_hints(extracted: ExtractedJobPosting) -> dict[str, ReviewProvenanceHint]:
    return {
        field_name: _provenance_hint(provenance)
        for field_name, provenance in extracted.field_provenance.items()
    }


def _provenance_hint(provenance: FieldProvenance) -> ReviewProvenanceHint:
    return ReviewProvenanceHint(
        field_name=provenance.field_name,
        source=provenance.source,
        confidence=provenance.confidence,
        note=provenance.note,
    )
