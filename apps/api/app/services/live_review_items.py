from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import cast
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LiveReviewItem
from app.schemas.extraction import RemoteType, ReviewStatus
from app.schemas.review import ReviewQueueItem, ReviewQueueStatusFilter


class LiveReviewItemStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_items(self, items: Sequence[ReviewQueueItem]) -> list[ReviewQueueItem]:
        rows: list[LiveReviewItem] = []
        for item in items:
            if item.synthetic or item.data_origin != "live_extraction":
                continue
            row = self._find_by_source_url(item.source_url)
            if row is None:
                row = LiveReviewItem(id=self._stable_row_id(item), source_url=item.source_url)
                self._session.add(row)
            self._apply_item(row, item)
            rows.append(row)
        self._session.flush()
        return [_row_to_item(row) for row in rows]

    def list_items(self, status: ReviewQueueStatusFilter = "all") -> list[ReviewQueueItem]:
        statement = select(LiveReviewItem).order_by(LiveReviewItem.created_at.desc())
        if status != "all":
            statement = statement.where(LiveReviewItem.review_status == status)
        return [_row_to_item(row) for row in self._session.scalars(statement).all()]

    def _find_by_source_url(self, source_url: str) -> LiveReviewItem | None:
        return self._session.scalar(
            select(LiveReviewItem).where(LiveReviewItem.source_url == source_url)
        )

    def _stable_row_id(self, item: ReviewQueueItem) -> str:
        if len(item.id) <= 240 and self._session.get(LiveReviewItem, item.id) is None:
            return item.id
        return str(uuid5(NAMESPACE_URL, item.source_url))

    @staticmethod
    def _apply_item(row: LiveReviewItem, item: ReviewQueueItem) -> None:
        row.source = _truncate(item.source, 120)
        row.external_id = _truncate(item.external_id, 240)
        row.source_url = item.source_url
        row.application_url = item.application_url
        row.title = _truncate(item.title, 240)
        row.company = _truncate(item.company, 240)
        row.locations = list(item.locations)
        row.remote_type = item.remote_type
        row.salary_min = item.salary_min
        row.salary_max = item.salary_max
        row.salary_currency = item.salary_currency
        row.employment_type = item.employment_type
        row.posted_date = _date_to_datetime(item.posted_date)
        row.valid_through = _date_to_datetime(item.valid_through)
        row.required_skills = list(item.required_skills)
        row.preferred_skills = list(item.preferred_skills)
        row.review_status = item.review_status
        row.review_reasons = list(item.review_reasons)
        row.extraction_confidence = Decimal(str(item.extraction_confidence))
        row.provenance_hints = {
            field_name: hint.model_dump(mode="json")
            for field_name, hint in item.provenance_hints.items()
        }
        row.data_origin = "live_extraction"


def _row_to_item(row: LiveReviewItem) -> ReviewQueueItem:
    return ReviewQueueItem(
        id=row.id,
        source=row.source,
        external_id=row.external_id,
        source_url=row.source_url,
        application_url=row.application_url,
        title=row.title,
        company=row.company,
        locations=tuple(row.locations or ()),
        remote_type=cast(RemoteType, row.remote_type),
        salary_min=row.salary_min,
        salary_max=row.salary_max,
        salary_currency=row.salary_currency,
        employment_type=row.employment_type,
        posted_date=_datetime_to_date(row.posted_date),
        valid_through=_datetime_to_date(row.valid_through),
        required_skills=tuple(row.required_skills or ()),
        preferred_skills=tuple(row.preferred_skills or ()),
        review_status=cast(ReviewStatus, row.review_status),
        review_reasons=tuple(row.review_reasons or ()),
        extraction_confidence=float(row.extraction_confidence),
        provenance_hints=row.provenance_hints or {},
        synthetic=False,
        data_origin="live_extraction",
        fixture_name=None,
    )


def _truncate(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    return value[:length]


def _date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=UTC)


def _datetime_to_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    return value.date()
