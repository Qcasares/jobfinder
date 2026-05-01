from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.models import SourcePolicy
from app.schemas.audit import ActorType
from app.schemas.policy import PolicyAction, PolicyDecision, PolicyStatus
from app.services.audit import AuditEventService


class SourcePolicyConfigurationError(ValueError):
    """Raised when persisted source policy actions are not valid policy actions."""


@dataclass(frozen=True)
class SourcePolicyRecord:
    source_id: str
    policy_id: str
    allowed_actions: frozenset[PolicyAction]
    denied_actions: frozenset[PolicyAction]
    reason: str
    expires_at: datetime | None = None


class SourcePolicyService:
    def __init__(self, audit_service: AuditEventService | None = None) -> None:
        self._policies: dict[str, SourcePolicyRecord] = {}
        self._audit_service = audit_service

    def register_policy(
        self,
        *,
        source_id: str,
        policy_id: str,
        allowed_actions: set[PolicyAction],
        denied_actions: set[PolicyAction],
        reason: str,
        expires_at: datetime | None = None,
    ) -> None:
        overlap = allowed_actions & denied_actions
        if overlap:
            actions = ", ".join(sorted(action.value for action in overlap))
            raise SourcePolicyConfigurationError(
                f"policy {policy_id} both allows and denies: {actions}"
            )
        self._policies[source_id] = SourcePolicyRecord(
            source_id=source_id,
            policy_id=policy_id,
            allowed_actions=frozenset(allowed_actions),
            denied_actions=frozenset(denied_actions),
            reason=reason,
            expires_at=expires_at,
        )

    def register_persisted_policy(self, policy: SourcePolicy) -> None:
        evidence_expires_at = self._earliest_expiry(
            [evidence.expires_at for evidence in policy.evidence_items]
        )
        self.register_policy(
            source_id=policy.source_id,
            policy_id=policy.id,
            allowed_actions=self._parse_actions(policy.allowed_actions),
            denied_actions=self._parse_actions(policy.denied_actions),
            reason=policy.reason,
            expires_at=self._earliest_expiry([policy.effective_to, evidence_expires_at]),
        )

    def decide(self, source_id: str, action: PolicyAction) -> PolicyDecision:
        policy = self._policies.get(source_id)
        if policy is None:
            decision = PolicyDecision(
                allowed=False,
                action=action,
                status=PolicyStatus.UNKNOWN_SOURCE,
                reason="Unknown source: action denied by default.",
                source_id=source_id,
                policy_id=None,
            )
            self._audit_decision(decision)
            return decision

        if self._is_expired(policy.expires_at):
            decision = PolicyDecision(
                allowed=False,
                action=action,
                status=PolicyStatus.REVIEW_REQUIRED,
                reason="Source policy evidence is expired; manual review is required.",
                source_id=source_id,
                policy_id=policy.policy_id,
            )
            self._audit_decision(decision)
            return decision

        if action in policy.denied_actions:
            decision = PolicyDecision(
                allowed=False,
                action=action,
                status=PolicyStatus.DENIED,
                reason=policy.reason,
                source_id=source_id,
                policy_id=policy.policy_id,
            )
            self._audit_decision(decision)
            return decision

        if action in policy.allowed_actions:
            decision = PolicyDecision(
                allowed=True,
                action=action,
                status=PolicyStatus.ALLOWED,
                reason=policy.reason,
                source_id=source_id,
                policy_id=policy.policy_id,
            )
            self._audit_decision(decision)
            return decision

        decision = PolicyDecision(
            allowed=False,
            action=action,
            status=PolicyStatus.NOT_ALLOWED,
            reason="Action is not explicitly allowed by this source policy.",
            source_id=source_id,
            policy_id=policy.policy_id,
        )
        self._audit_decision(decision)
        return decision

    @staticmethod
    def _parse_actions(raw_actions: list[str]) -> set[PolicyAction]:
        actions: set[PolicyAction] = set()
        for raw_action in raw_actions:
            try:
                actions.add(PolicyAction(raw_action))
            except ValueError as exc:
                raise SourcePolicyConfigurationError(
                    f"unknown source policy action: {raw_action}"
                ) from exc
        return actions

    @staticmethod
    def _earliest_expiry(expires_at_values: list[datetime | None]) -> datetime | None:
        concrete_values = [value for value in expires_at_values if value is not None]
        if not concrete_values:
            return None
        return min(concrete_values)

    @staticmethod
    def _is_expired(expires_at: datetime | None) -> bool:
        if expires_at is None:
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC)

    def _audit_decision(self, decision: PolicyDecision) -> None:
        if self._audit_service is None:
            return
        self._audit_service.create_event(
            event_type="source_policy.decision",
            actor_type=ActorType.SYSTEM,
            actor_id="source-policy-service",
            correlation_id=f"policy:{decision.source_id}:{decision.action.value}",
            payload={
                "source_id": decision.source_id,
                "policy_id": decision.policy_id,
                "action": decision.action.value,
                "status": decision.status.value,
                "allowed": decision.allowed,
            },
        )
