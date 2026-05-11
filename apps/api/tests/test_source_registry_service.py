from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import SourcePolicyEvidence
from app.schemas.policy import PolicyAction, PolicyStatus
from app.services.source_registry import SourceRegistryService


def test_source_registry_upserts_sources_and_evaluates_persisted_allow_policy() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        service = SourceRegistryService(session)
        source = service.upsert_source(
            domain="https://www.Greenhouse.io:443/jobs",
            name="Greenhouse",
            source_type="official_ats",
        )
        policy = service.attach_source_policy(
            source_id=source.id,
            status="approved",
            reason="Official integration permits read workflow.",
            allowed_actions=[PolicyAction.DISCOVER, PolicyAction.EXTRACT],
            denied_actions=[PolicyAction.SUBMIT],
            evidence=[
                {
                    "evidence_type": "synthetic_policy_review",
                    "url": "https://example.test/policy",
                    "excerpt": "Synthetic policy summary for tests.",
                }
            ],
        )

        decision = service.evaluate_action(domain="greenhouse.io", action=PolicyAction.EXTRACT)

    assert source.domain == "greenhouse.io"
    assert policy.source_id == source.id
    assert decision.allowed is True
    assert decision.status is PolicyStatus.ALLOWED
    assert decision.policy_id == policy.id


def test_source_registry_denies_unknown_domains_by_default() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        decision = SourceRegistryService(session).evaluate_action(
            domain="missing.example",
            action=PolicyAction.DRAFT,
        )

    assert decision.allowed is False
    assert decision.status is PolicyStatus.UNKNOWN_SOURCE
    assert decision.source_id == "missing.example"


def test_source_registry_requires_review_when_policy_evidence_is_expired() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        service = SourceRegistryService(session)
        source = service.upsert_source(
            domain="https://jobs.example.test",
            name="Synthetic Jobs",
            source_type="official_ats",
        )
        policy = service.attach_source_policy(
            source_id=source.id,
            status="approved",
            reason="Synthetic approval expired.",
            allowed_actions=[PolicyAction.DISCOVER, PolicyAction.EXTRACT],
            denied_actions=[],
            evidence=[
                {
                    "evidence_type": "synthetic_policy_review",
                    "url": "https://example.test/policy",
                    "excerpt": "Synthetic policy summary for tests.",
                    "expires_at": datetime.now(UTC) - timedelta(days=1),
                }
            ],
        )

        decision = service.evaluate_action(
            domain="jobs.example.test",
            action=PolicyAction.EXTRACT,
        )
        evidence = session.scalars(select(SourcePolicyEvidence)).one()

    assert policy.id == decision.policy_id
    assert evidence.expires_at is not None
    assert decision.allowed is False
    assert decision.status is PolicyStatus.REVIEW_REQUIRED
    assert "expired" in decision.reason


def test_seed_known_source_policies_allows_live_boards_and_denies_prohibited_actions() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        service = SourceRegistryService(session)
        policies = service.seed_known_source_policies()
        linkedin_decision = service.evaluate_action(
            domain="www.linkedin.com",
            action=PolicyAction.DISCOVER,
        )
        reed_decision = service.evaluate_action(
            domain="www.reed.co.uk",
            action=PolicyAction.DISCOVER,
        )
        reed_submit_decision = service.evaluate_action(
            domain="reed.co.uk",
            action=PolicyAction.SUBMIT,
        )
        indeed_decision = service.evaluate_action(
            domain="indeed.com",
            action=PolicyAction.SUBMIT,
        )
        evidence = session.scalars(select(SourcePolicyEvidence)).all()

    assert len(policies) == 7
    assert reed_decision.allowed is True
    assert reed_decision.status is PolicyStatus.ALLOWED
    assert reed_submit_decision.allowed is False
    assert reed_submit_decision.status is PolicyStatus.DENIED
    assert linkedin_decision.allowed is False
    assert linkedin_decision.status is PolicyStatus.DENIED
    assert indeed_decision.allowed is False
    assert indeed_decision.status is PolicyStatus.DENIED
    assert {item.evidence_type for item in evidence} == {"operator_source_review"}
