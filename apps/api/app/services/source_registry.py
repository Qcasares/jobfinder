from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Source, SourcePolicy, SourcePolicyEvidence
from app.schemas.policy import PolicyAction, PolicyDecision
from app.schemas.source_registry import SourcePolicyEvidenceCreate
from app.services.audit import AuditEventService
from app.services.domain import normalize_domain
from app.services.policy import SourcePolicyService

SourcePolicyEvidenceInput = dict[str, str | datetime | None] | SourcePolicyEvidenceCreate


class SourceRegistryService:
    def __init__(
        self,
        session: Session,
        *,
        policy_service: SourcePolicyService | None = None,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._session = session
        self._policy_service = policy_service or SourcePolicyService(audit_service=audit_service)

    def upsert_source(
        self,
        *,
        domain: str,
        name: str | None = None,
        source_type: str = "job_board",
        base_url: str | None = None,
    ) -> Source:
        normalized_domain = normalize_domain(domain)
        source = self._session.scalar(select(Source).where(Source.domain == normalized_domain))
        if source is None:
            source = Source(
                id=str(uuid4()),
                name=name or normalized_domain,
                source_type=source_type,
                base_url=base_url,
                domain=normalized_domain,
            )
            self._session.add(source)
        else:
            source.name = name or source.name
            source.source_type = source_type
            source.base_url = base_url if base_url is not None else source.base_url
        self._session.flush()
        return source

    def list_sources(self) -> list[Source]:
        return list(
            self._session.scalars(
                select(Source).options(selectinload(Source.policies)).order_by(Source.domain)
            )
        )

    def list_policies(self) -> list[SourcePolicy]:
        return list(
            self._session.scalars(
                select(SourcePolicy)
                .options(selectinload(SourcePolicy.evidence_items))
                .order_by(SourcePolicy.effective_from.desc(), SourcePolicy.id)
            )
        )

    def attach_source_policy(
        self,
        *,
        source_id: str,
        status: str,
        reason: str,
        allowed_actions: Sequence[PolicyAction],
        denied_actions: Sequence[PolicyAction],
        evidence: Sequence[SourcePolicyEvidenceInput],
    ) -> SourcePolicy:
        policy = SourcePolicy(
            id=str(uuid4()),
            source_id=source_id,
            status=status,
            reason=reason,
            allowed_actions=[action.value for action in allowed_actions],
            denied_actions=[action.value for action in denied_actions],
            effective_from=datetime.now(UTC),
        )
        self._session.add(policy)
        self._session.flush()
        self._replace_policy_evidence(policy.id, evidence)
        self._session.flush()
        self._policy_service.register_persisted_policy(policy)
        return policy

    def evaluate_action(
        self,
        *,
        action: PolicyAction,
        domain: str | None = None,
        source_id: str | None = None,
    ) -> PolicyDecision:
        self.register_persisted_policies()
        if source_id is not None:
            return self._policy_service.decide(source_id, action)

        if domain is None:
            raise ValueError("domain or source_id is required")

        normalized_domain = normalize_domain(domain)
        source = self._session.scalar(select(Source).where(Source.domain == normalized_domain))
        if source is None:
            return self._policy_service.decide(normalized_domain, action)
        return self._policy_service.decide(source.id, action)

    def register_persisted_policies(self) -> None:
        for policy in self._latest_active_policies():
            self._policy_service.register_persisted_policy(policy)

    def seed_known_source_policies(self) -> list[SourcePolicy]:
        policies: list[SourcePolicy] = []
        for known in KNOWN_GOVERNED_LIVE_SOURCES:
            source = self.upsert_source(
                domain=known["domain"],
                name=known["name"],
                source_type="public_job_board",
                base_url=f"https://{known['domain']}",
            )
            policy = self._upsert_latest_policy(
                source_id=source.id,
                status="approved",
                reason=KNOWN_GOVERNED_LIVE_REASON,
                allowed_actions=[PolicyAction.DISCOVER, PolicyAction.EXTRACT],
                denied_actions=[PolicyAction.DRAFT, PolicyAction.AUTOFILL, PolicyAction.SUBMIT],
                evidence=[
                    SourcePolicyEvidenceCreate(
                        evidence_type="operator_source_review",
                        url=f"https://{known['domain']}",
                        excerpt=(
                            "Approved for bounded operator-queued public page discovery and "
                            "extraction. Stop at login, CAPTCHA, bot-detection, access controls, "
                            "or external submission."
                        ),
                    )
                ],
            )
            policies.append(policy)

        for known in KNOWN_PROHIBITED_SOURCES:
            source = self.upsert_source(
                domain=known["domain"],
                name=known["name"],
                source_type="prohibited_platform",
                base_url=f"https://{known['domain']}",
            )
            policy = self._upsert_latest_policy(
                source_id=source.id,
                status="prohibited",
                reason=KNOWN_PROHIBITED_REASON,
                allowed_actions=[],
                denied_actions=list(PolicyAction),
                evidence=[
                    SourcePolicyEvidenceCreate(
                        evidence_type="operator_source_review",
                        url=f"https://{known['domain']}",
                        excerpt=(
                            "Automated workflow is denied unless an approved official integration "
                            "is configured."
                        ),
                    )
                ],
            )
            policies.append(policy)
        return policies

    def _latest_active_policies(self) -> list[SourcePolicy]:
        policies = self._session.scalars(
            select(SourcePolicy)
            .where(SourcePolicy.effective_to.is_(None))
            .order_by(SourcePolicy.source_id, SourcePolicy.effective_from, SourcePolicy.created_at)
        ).all()
        latest_by_source: dict[str, SourcePolicy] = {}
        for policy in policies:
            latest_by_source[policy.source_id] = policy
        return list(latest_by_source.values())

    def _upsert_latest_policy(
        self,
        *,
        source_id: str,
        status: str,
        reason: str,
        allowed_actions: Sequence[PolicyAction],
        denied_actions: Sequence[PolicyAction],
        evidence: Sequence[SourcePolicyEvidenceCreate],
    ) -> SourcePolicy:
        policy = self._session.scalar(
            select(SourcePolicy)
            .where(SourcePolicy.source_id == source_id, SourcePolicy.effective_to.is_(None))
            .order_by(SourcePolicy.effective_from.desc(), SourcePolicy.created_at.desc())
            .limit(1)
        )
        if policy is None:
            return self.attach_source_policy(
                source_id=source_id,
                status=status,
                reason=reason,
                allowed_actions=allowed_actions,
                denied_actions=denied_actions,
                evidence=evidence,
            )

        policy.status = status
        policy.reason = reason
        policy.allowed_actions = [action.value for action in allowed_actions]
        policy.denied_actions = [action.value for action in denied_actions]
        self._replace_policy_evidence(policy.id, evidence)
        self._session.flush()
        self._policy_service.register_persisted_policy(policy)
        return policy

    def _replace_policy_evidence(
        self,
        policy_id: str,
        evidence: Sequence[SourcePolicyEvidenceInput],
    ) -> None:
        self._session.execute(
            delete(SourcePolicyEvidence).where(SourcePolicyEvidence.source_policy_id == policy_id)
        )
        for item in evidence:
            evidence_item = (
                item
                if isinstance(item, SourcePolicyEvidenceCreate)
                else SourcePolicyEvidenceCreate(**item)
            )
            self._session.add(
                SourcePolicyEvidence(
                    id=str(uuid4()),
                    source_policy_id=policy_id,
                    evidence_type=evidence_item.evidence_type,
                    url=evidence_item.url,
                    excerpt=evidence_item.excerpt,
                    expires_at=evidence_item.expires_at,
                    captured_at=datetime.now(UTC),
                )
            )


KNOWN_GOVERNED_LIVE_REASON = (
    "Approved for bounded operator-queued public page discovery and extraction only; stop on "
    "login, CAPTCHA, bot detection, access controls, autofill, or external submission."
)


KNOWN_GOVERNED_LIVE_SOURCES = [
    {"domain": "reed.co.uk", "name": "Reed"},
    {"domain": "hays.co.uk", "name": "Hays"},
    {"domain": "totaljobs.com", "name": "Totaljobs"},
    {"domain": "cityjobs.com", "name": "CityJobs"},
    {"domain": "efinancialcareers.co.uk", "name": "eFinancialCareers"},
]


KNOWN_PROHIBITED_REASON = (
    "Manual-only/prohibited source policy: deny discover, extract, draft, autofill, and submit "
    "unless an approved official integration exists."
)

KNOWN_PROHIBITED_SOURCES = [
    {"domain": "linkedin.com", "name": "LinkedIn"},
    {"domain": "indeed.com", "name": "Indeed"},
]
