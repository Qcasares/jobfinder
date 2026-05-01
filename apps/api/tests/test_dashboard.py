from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard import DashboardService


def test_dashboard_service_returns_typed_synthetic_summary() -> None:
    summary = DashboardService().get_summary()

    validated = DashboardSummary.model_validate(summary.model_dump())

    assert validated.counts.job_postings >= 0
    assert validated.status.policy_mode == "governed"
    assert len(validated.audit_feed) > 0
    assert all(item.synthetic for item in validated.audit_feed)


def test_dashboard_summary_endpoint_returns_seeded_data() -> None:
    client = TestClient(create_app())

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    summary = DashboardSummary.model_validate(response.json())
    assert summary.status.service == "jobfinder-api"
    assert summary.status.database == "unavailable_static_seed"
