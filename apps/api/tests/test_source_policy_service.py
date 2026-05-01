from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import SourcePolicy
from app.schemas.policy import PolicyAction, PolicyStatus
from app.services.audit import AuditEventService
from app.services.policy import SourcePolicyConfigurationError, SourcePolicyService


def test_unknown_source_denies_every_action() -> None:
    service = SourcePolicyService()

    for action in PolicyAction:
        decision = service.decide(source_id="missing-source", action=action)

        assert decision.allowed is False
        assert decision.action is action
        assert decision.status is PolicyStatus.UNKNOWN_SOURCE
        assert decision.source_id == "missing-source"
        assert decision.policy_id is None


def test_explicit_policy_allow_and_deny_are_action_scoped() -> None:
    service = SourcePolicyService()
    service.register_policy(
        source_id="greenhouse",
        policy_id="policy-greenhouse",
        allowed_actions={PolicyAction.DISCOVER, PolicyAction.EXTRACT, PolicyAction.DRAFT},
        denied_actions={PolicyAction.SUBMIT},
        reason="official API permits read workflow; submit requires manual approval",
    )

    allow_decision = service.decide("greenhouse", PolicyAction.EXTRACT)
    deny_decision = service.decide("greenhouse", PolicyAction.SUBMIT)
    unspecified_decision = service.decide("greenhouse", PolicyAction.AUTOFILL)

    assert allow_decision.allowed is True
    assert allow_decision.status is PolicyStatus.ALLOWED
    assert allow_decision.policy_id == "policy-greenhouse"

    assert deny_decision.allowed is False
    assert deny_decision.status is PolicyStatus.DENIED
    assert deny_decision.policy_id == "policy-greenhouse"

    assert unspecified_decision.allowed is False
    assert unspecified_decision.status is PolicyStatus.NOT_ALLOWED
    assert unspecified_decision.policy_id == "policy-greenhouse"


def test_expired_policy_requires_manual_review_before_allowed_actions() -> None:
    service = SourcePolicyService()
    service.register_policy(
        source_id="greenhouse",
        policy_id="policy-greenhouse",
        allowed_actions={PolicyAction.DISCOVER, PolicyAction.EXTRACT},
        denied_actions={PolicyAction.SUBMIT},
        reason="Official integration permits read workflow.",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )

    decision = service.decide("greenhouse", PolicyAction.EXTRACT)

    assert decision.allowed is False
    assert decision.status is PolicyStatus.REVIEW_REQUIRED
    assert decision.policy_id == "policy-greenhouse"
    assert "expired" in decision.reason


def test_persisted_policy_actions_are_validated_before_registration() -> None:
    service = SourcePolicyService()
    policy = SourcePolicy(
        id="policy-1",
        source_id="source-1",
        status="reviewed",
        reason="official job board API permits read workflow",
        allowed_actions=["discover", "extract"],
        denied_actions=["submit"],
        effective_from=datetime.now(UTC),
    )

    service.register_persisted_policy(policy)

    assert service.decide("source-1", PolicyAction.DISCOVER).allowed is True
    assert service.decide("source-1", PolicyAction.SUBMIT).status is PolicyStatus.DENIED


def test_persisted_policy_rejects_unknown_actions() -> None:
    service = SourcePolicyService()
    policy = SourcePolicy(
        id="policy-1",
        source_id="source-1",
        status="reviewed",
        reason="invalid action should not be accepted",
        allowed_actions=["crawl"],
        denied_actions=[],
        effective_from=datetime.now(UTC),
    )

    with pytest.raises(SourcePolicyConfigurationError):
        service.register_persisted_policy(policy)


def test_policy_decisions_emit_audit_events_when_audit_service_is_configured() -> None:
    audit_service = AuditEventService()
    service = SourcePolicyService(audit_service=audit_service)

    decision = service.decide("unknown", PolicyAction.DRAFT)

    events = audit_service.list_events()
    assert decision.allowed is False
    assert len(events) == 1
    assert events[0].event_type == "source_policy.decision"
    assert events[0].payload["source_id"] == "unknown"
    assert events[0].payload["action"] == "draft"
