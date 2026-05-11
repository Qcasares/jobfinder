from datetime import UTC, datetime

from app.schemas.dashboard import (
    DashboardAuditFeedItem,
    DashboardCounts,
    DashboardStatus,
    DashboardSummary,
)


class DashboardService:
    def __init__(self, service_name: str = "jobfinder-api") -> None:
        self._service_name = service_name

    def get_summary(self) -> DashboardSummary:
        now = datetime.now(UTC)
        return DashboardSummary(
            counts=DashboardCounts(
                job_postings=3,
                approval_requests=1,
                applications=0,
                audit_events=2,
            ),
            status=DashboardStatus(
                service=self._service_name,
                database="unavailable_static_seed",
                policy_mode="governed",
            ),
            audit_feed=[
                DashboardAuditFeedItem(
                    event_type="policy.seeded",
                    actor="system",
                    summary="Governed source policy registry initialized.",
                    created_at=now,
                ),
                DashboardAuditFeedItem(
                    event_type="dashboard.seeded",
                    actor="system",
                    summary="Dashboard counts loaded without live candidate data.",
                    created_at=now,
                ),
            ],
        )
