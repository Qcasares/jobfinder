from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Application, ApprovalRequest, JobPosting
from app.schemas.applications import ApplicationRead, ApplicationSafety, ApplicationSummary


class ApplicationTrackerService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_applications(self) -> list[ApplicationRead]:
        rows = self._session.execute(
            select(Application, JobPosting, ApprovalRequest)
            .join(JobPosting, Application.job_posting_id == JobPosting.id)
            .outerjoin(ApprovalRequest, Application.approval_request_id == ApprovalRequest.id)
            .order_by(Application.created_at, Application.id)
        ).all()
        return [self._read(application, job) for application, job, _approval in rows]

    def get_summary(self) -> ApplicationSummary:
        applications = self.list_applications()
        return ApplicationSummary(
            total=len(applications),
            not_started=sum(
                1 for application in applications if application.status == "not_started"
            ),
            in_review=sum(
                1 for application in applications if application.status == "ready_for_review"
            ),
            approved=sum(1 for application in applications if application.status == "approved"),
            submitted=sum(1 for application in applications if application.safety.submit_performed),
            external_side_effects=sum(
                1 for application in applications if application.safety.external_side_effect
            ),
        )

    @staticmethod
    def _read(application: Application, job: JobPosting) -> ApplicationRead:
        submit_performed = application.status == "submitted" or application.submitted_at is not None
        return ApplicationRead(
            id=application.id,
            job_posting_id=application.job_posting_id,
            approval_request_id=application.approval_request_id,
            job_title=job.title,
            company=job.company,
            status=application.status,
            application_url=application.application_url,
            submitted_at=application.submitted_at,
            created_at=application.created_at,
            updated_at=application.updated_at,
            synthetic=True,
            safety=ApplicationSafety(
                submit_performed=submit_performed,
                autofill_performed=False,
                external_side_effect=submit_performed,
            ),
        )
