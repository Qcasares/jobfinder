from __future__ import annotations

from collections.abc import Sequence

from app.schemas.jobs import JobListItem, JobStatusFilter, JobSummary
from app.schemas.review import ReviewQueueItem
from app.services.review_queue import ReviewQueueService


class JobCatalogService:
    def __init__(
        self,
        *,
        review_queue: ReviewQueueService | None = None,
        live_review_items: Sequence[ReviewQueueItem] | None = None,
    ) -> None:
        self._review_queue = review_queue or ReviewQueueService()
        self._live_review_items = tuple(live_review_items or ())

    def list_jobs(self, status: JobStatusFilter = "all") -> list[JobListItem]:
        items = [
            *self._review_queue.list_items(status=status),
            *(
                item
                for item in self._live_review_items
                if status == "all" or item.review_status == status
            ),
        ]
        return [
            JobListItem(
                id=item.id,
                source=item.source,
                external_id=item.external_id,
                title=item.title,
                company=item.company,
                locations=item.locations,
                remote_type=item.remote_type,
                salary_min=item.salary_min,
                salary_max=item.salary_max,
                salary_currency=item.salary_currency,
                employment_type=item.employment_type,
                posted_date=item.posted_date,
                valid_through=item.valid_through,
                source_url=item.source_url,
                application_url=item.application_url,
                review_status=item.review_status,
                review_reasons=item.review_reasons,
                extraction_confidence=item.extraction_confidence,
                required_skills=item.required_skills,
                preferred_skills=item.preferred_skills,
                fixture_name=item.fixture_name,
                synthetic=item.synthetic,
            )
            for item in items
        ]

    def get_summary(self) -> JobSummary:
        jobs = self.list_jobs()
        return JobSummary(
            total=len(jobs),
            ready=sum(1 for job in jobs if job.review_status == "ready"),
            needs_review=sum(1 for job in jobs if job.review_status == "needs_review"),
            remote=sum(1 for job in jobs if job.remote_type == "remote"),
            hybrid=sum(1 for job in jobs if job.remote_type == "hybrid"),
            onsite=sum(1 for job in jobs if job.remote_type == "onsite"),
            unknown_remote=sum(1 for job in jobs if job.remote_type == "unknown"),
        )
