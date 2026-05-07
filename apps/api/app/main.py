from collections.abc import Awaitable, Callable, Iterator
from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import Source, SourcePolicy
from app.db.session import get_db_session
from app.schemas.applications import ApplicationRead, ApplicationSummary
from app.schemas.approvals import (
    ApprovalDecisionCreate,
    ApprovalRequestCreate,
    ApprovalRequestRead,
    ApprovalRequestSummary,
)
from app.schemas.audit_explorer import (
    AuditChainVerification,
    AuditExplorerEvent,
    AuditExplorerSummary,
)
from app.schemas.autofill import AutofillPacketRead, AutofillPacketRequest
from app.schemas.candidate import (
    CandidateDocumentRecordCreate,
    CandidateDocumentRecordRead,
    CandidateEvidenceCreate,
    CandidateEvidenceRead,
    CandidateProfileRead,
    CandidateProfileUpdate,
    CandidateWorkspaceRead,
    SearchCriteriaCreate,
    SearchCriteriaRead,
)
from app.schemas.dashboard import DashboardSummary
from app.schemas.drafting import DraftingRequest, DraftingRunRead
from app.schemas.final_review import FinalReviewPacketRead, FinalReviewPacketRequest
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobListItem, JobStatusFilter, JobSummary
from app.schemas.live_discovery import (
    LiveDiscoveryRequest,
    LiveDiscoveryRun,
    LiveSearchDiscoveryRequest,
)
from app.schemas.policy import PolicyDecision
from app.schemas.review import ReviewQueueItem, ReviewQueueStatusFilter, ReviewQueueSummary
from app.schemas.runtime_settings import RuntimeSettingsRead
from app.schemas.source_registry import (
    SourcePolicyCheckRequest,
    SourcePolicyEvidenceRead,
    SourcePolicyRead,
    SourcePolicySummary,
    SourceRead,
    SourceUpsertRequest,
    actions_from_raw,
)
from app.services.applications import ApplicationTrackerService
from app.services.approvals import (
    ApprovalRequestNotFoundError,
    ApprovalRequestService,
    InvalidApprovalTransitionError,
    ReviewItemNotFoundError,
)
from app.services.audit import AuditEventService
from app.services.audit_explorer import AuditExplorerService
from app.services.autofill import AutofillPacketService
from app.services.candidate import CandidateSafetyError, CandidateWorkspaceService
from app.services.dashboard import DashboardService
from app.services.domain import DomainNormalizationError
from app.services.drafting import DraftingProvider, DraftingSafetyError, DraftingService
from app.services.final_review import FinalReviewPacketService
from app.services.jobs import JobCatalogService
from app.services.live_discovery import FetchFunction, LiveDiscoveryService
from app.services.production_guard import WRITE_API_DISABLED_DETAIL
from app.services.review_queue import ReviewQueueService
from app.services.runtime_settings import RuntimeSettingsService
from app.services.source_registry import SourceRegistryService

WRITE_GATED_ROUTES = {
    "/approvals/requests",
    "/candidate/evidence",
    "/candidate/document-records",
    "/candidate/profile",
    "/candidate/search-criteria",
    "/source-policies/seed-known",
    "/sources",
}

OPERATOR_GATED_ROUTES = WRITE_GATED_ROUTES | {
    "/autofill/packets",
    "/drafting/runs",
    "/final-review/packets",
    "/live-discovery/runs",
    "/live-discovery/search-runs",
}

OPERATOR_KEY_HEADER = "x-jobfinder-operator-key"
OPERATOR_KEY_NOT_CONFIGURED_DETAIL = "Operator API key is not configured."
OPERATOR_KEY_REQUIRED_DETAIL = "A valid operator API key is required."


def _is_operator_gated_request(request: Request) -> bool:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    if request.url.path in OPERATOR_GATED_ROUTES:
        return True
    return request.url.path.startswith("/approvals/requests/") and request.url.path.endswith(
        "/decision"
    )


def _operator_key_allowed(request: Request, settings: Settings) -> tuple[bool, str | None]:
    if not settings.production_operator_auth_required or not _is_operator_gated_request(request):
        return True, None
    if not settings.operator_api_key:
        return False, OPERATOR_KEY_NOT_CONFIGURED_DETAIL
    supplied_key = request.headers.get(OPERATOR_KEY_HEADER, "")
    if compare_digest(supplied_key, settings.operator_api_key):
        return True, None
    return False, OPERATOR_KEY_REQUIRED_DETAIL


def create_app(
    settings: Settings | None = None,
    *,
    live_discovery_fetcher: FetchFunction | None = None,
    drafting_provider: DraftingProvider | None = None,
    test_engine: Engine | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(title="Jobfinder API", version="0.1.0")
    live_discovery_service = LiveDiscoveryService(
        settings=resolved_settings,
        fetcher=live_discovery_fetcher,
    )

    @app.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        return response

    @app.middleware("http")
    async def production_operator_auth_guard(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        allowed, detail = _operator_key_allowed(request, resolved_settings)
        if not allowed:
            status_code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if detail == OPERATOR_KEY_NOT_CONFIGURED_DETAIL
                else status.HTTP_401_UNAUTHORIZED
            )
            return JSONResponse(status_code=status_code, content={"detail": detail})
        response = await call_next(request)
        return response

    @app.middleware("http")
    async def production_write_guard(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.url.path in WRITE_GATED_ROUTES
            and not resolved_settings.production_writes_allowed
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": WRITE_API_DISABLED_DETAIL},
            )
        response = await call_next(request)
        return response

    if resolved_settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_allowed_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["content-type", OPERATOR_KEY_HEADER],
            allow_credentials=False,
        )
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: resolved_settings
    if test_engine is not None:

        def get_test_db_session() -> Iterator[Session]:
            with Session(test_engine) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        app.dependency_overrides[get_db_session] = get_test_db_session

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service=resolved_settings.service_name)

    @app.get("/dashboard/summary", response_model=DashboardSummary)
    def dashboard_summary() -> DashboardSummary:
        return DashboardService(service_name=resolved_settings.service_name).get_summary()

    @app.get("/settings/runtime", response_model=RuntimeSettingsRead)
    def runtime_settings() -> RuntimeSettingsRead:
        return RuntimeSettingsService(resolved_settings).get_status()

    @app.get("/candidate/workspace", response_model=CandidateWorkspaceRead)
    def candidate_workspace(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CandidateWorkspaceRead:
        return CandidateWorkspaceService(session).get_workspace()

    @app.post("/candidate/profile", response_model=CandidateProfileRead)
    def update_candidate_profile(
        request: CandidateProfileUpdate,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CandidateProfileRead:
        try:
            return CandidateWorkspaceService(session).update_profile(request)
        except CandidateSafetyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/candidate/evidence", response_model=CandidateEvidenceRead)
    def create_candidate_evidence(
        request: CandidateEvidenceCreate,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CandidateEvidenceRead:
        try:
            return CandidateWorkspaceService(session).create_evidence(request)
        except CandidateSafetyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/candidate/document-records", response_model=CandidateDocumentRecordRead)
    def create_candidate_document_record(
        request: CandidateDocumentRecordCreate,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> CandidateDocumentRecordRead:
        try:
            return CandidateWorkspaceService(
                session,
                settings=resolved_settings,
            ).create_document_record(request)
        except CandidateSafetyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/candidate/search-criteria", response_model=SearchCriteriaRead)
    def create_candidate_search_criteria(
        request: SearchCriteriaCreate,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> SearchCriteriaRead:
        try:
            return CandidateWorkspaceService(session).create_search_criteria(request)
        except CandidateSafetyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/review/queue", response_model=list[ReviewQueueItem])
    def review_queue(status: ReviewQueueStatusFilter = "all") -> list[ReviewQueueItem]:
        return ReviewQueueService(
            raw_postings=(),
            fixture_specs=None,
        ).list_items(status=status) + [
            item
            for item in live_discovery_service.review_items()
            if status == "all" or item.review_status == status
        ]

    @app.get("/review/summary", response_model=ReviewQueueSummary)
    def review_summary() -> ReviewQueueSummary:
        items = review_queue(status="all")
        ready = sum(1 for item in items if item.review_status == "ready")
        needs_review = sum(1 for item in items if item.review_status == "needs_review")
        return ReviewQueueSummary(total=len(items), ready=ready, needs_review=needs_review)

    @app.get("/jobs", response_model=list[JobListItem])
    def list_jobs(status: JobStatusFilter = "all") -> list[JobListItem]:
        return JobCatalogService().list_jobs(status=status)

    @app.get("/jobs/summary", response_model=JobSummary)
    def jobs_summary() -> JobSummary:
        return JobCatalogService().get_summary()

    @app.post("/autofill/packets", response_model=AutofillPacketRead)
    def create_autofill_packet(
        request: AutofillPacketRequest,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> AutofillPacketRead:
        return AutofillPacketService(
            session,
            settings=resolved_settings,
        ).create_packet(request)

    @app.post("/final-review/packets", response_model=FinalReviewPacketRead)
    def create_final_review_packet(
        request: FinalReviewPacketRequest,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> FinalReviewPacketRead:
        return FinalReviewPacketService(
            session,
            settings=resolved_settings,
        ).create_packet(request)

    @app.post("/drafting/runs", response_model=DraftingRunRead)
    def create_drafting_run(
        request: DraftingRequest,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> DraftingRunRead:
        try:
            return DraftingService(
                session,
                settings=resolved_settings,
                provider=drafting_provider,
            ).create_draft(request)
        except DraftingSafetyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/live-discovery/runs", response_model=LiveDiscoveryRun)
    def create_live_discovery_run(
        request: LiveDiscoveryRequest,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> LiveDiscoveryRun:
        return live_discovery_service.run(request, session=session)

    @app.get("/live-discovery/runs/{run_id}", response_model=LiveDiscoveryRun)
    def get_live_discovery_run(run_id: str) -> LiveDiscoveryRun:
        run = live_discovery_service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Live discovery run not found.")
        return run

    @app.post("/live-discovery/search-runs", response_model=LiveDiscoveryRun)
    def create_live_search_discovery_run(
        request: LiveSearchDiscoveryRequest,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> LiveDiscoveryRun:
        return live_discovery_service.run_search_discovery(request, session=session)

    @app.get("/live-discovery/search-runs/{run_id}", response_model=LiveDiscoveryRun)
    def get_live_search_discovery_run(run_id: str) -> LiveDiscoveryRun:
        run = live_discovery_service.get_search_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Live search discovery run not found.")
        return run

    @app.get("/approvals/requests", response_model=list[ApprovalRequestRead])
    def list_approval_requests(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> list[ApprovalRequestRead]:
        return ApprovalRequestService(session).list_requests()

    @app.get("/approvals/summary", response_model=ApprovalRequestSummary)
    def approval_summary(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> ApprovalRequestSummary:
        return ApprovalRequestService(session).get_summary()

    @app.post("/approvals/requests", response_model=ApprovalRequestRead)
    def create_approval_request(
        request: ApprovalRequestCreate,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> ApprovalRequestRead:
        try:
            return ApprovalRequestService(session).create_request(request)
        except ReviewItemNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/approvals/requests/{request_id}/decision", response_model=ApprovalRequestRead)
    def decide_approval_request(
        request_id: str,
        decision: ApprovalDecisionCreate,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> ApprovalRequestRead:
        try:
            return ApprovalRequestService(session).record_decision(request_id, decision)
        except ApprovalRequestNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidApprovalTransitionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/applications", response_model=list[ApplicationRead])
    def list_applications(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> list[ApplicationRead]:
        return ApplicationTrackerService(session).list_applications()

    @app.get("/applications/summary", response_model=ApplicationSummary)
    def applications_summary(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> ApplicationSummary:
        return ApplicationTrackerService(session).get_summary()

    @app.get("/audit/events", response_model=list[AuditExplorerEvent])
    def list_audit_events(
        session: Annotated[Session, Depends(get_db_session)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        correlation_id: str | None = None,
    ) -> list[AuditExplorerEvent]:
        return AuditExplorerService(session).list_events(
            limit=limit,
            correlation_id=correlation_id,
        )

    @app.get("/audit/summary", response_model=AuditExplorerSummary)
    def audit_summary(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> AuditExplorerSummary:
        return AuditExplorerService(session).get_summary()

    @app.get("/audit/verify-chain", response_model=AuditChainVerification)
    def verify_audit_chain(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> AuditChainVerification:
        return AuditExplorerService(session).verify_chain()

    @app.get("/sources", response_model=list[SourceRead])
    def list_sources(session: Annotated[Session, Depends(get_db_session)]) -> list[SourceRead]:
        sources = SourceRegistryService(session).list_sources()
        return [_source_read(source) for source in sources]

    @app.post("/sources", response_model=SourceRead)
    def upsert_source(
        request: SourceUpsertRequest,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> SourceRead:
        try:
            source = SourceRegistryService(session).upsert_source(
                domain=request.domain,
                name=request.name,
                source_type=request.source_type,
                base_url=request.base_url,
            )
        except DomainNormalizationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _source_read(source)

    @app.get("/source-policies", response_model=list[SourcePolicyRead])
    def list_source_policies(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> list[SourcePolicyRead]:
        policies = SourceRegistryService(session).list_policies()
        return [_policy_read(policy) for policy in policies]

    @app.post("/source-policies/check", response_model=PolicyDecision)
    def check_source_policy(
        request: SourcePolicyCheckRequest,
        session: Annotated[Session, Depends(get_db_session)],
    ) -> PolicyDecision:
        try:
            decision = SourceRegistryService(
                session,
                audit_service=AuditEventService(session=session),
            ).evaluate_action(
                domain=request.domain,
                source_id=request.source_id,
                action=request.action,
            )
        except DomainNormalizationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return decision

    @app.post("/source-policies/seed-known", response_model=list[SourcePolicyRead])
    def seed_known_source_policies(
        session: Annotated[Session, Depends(get_db_session)],
    ) -> list[SourcePolicyRead]:
        policies = SourceRegistryService(session).seed_known_source_policies()
        return [_policy_read(policy) for policy in policies]

    return app


def _source_read(source: Source) -> SourceRead:
    return SourceRead(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        base_url=source.base_url,
        domain=source.domain,
        created_at=source.created_at,
        updated_at=source.updated_at,
        latest_policy=_latest_policy_summary(source),
    )


def _latest_policy_summary(source: Source) -> SourcePolicySummary | None:
    active_policies = [policy for policy in source.policies if policy.effective_to is None]
    if not active_policies:
        return None
    policy = max(active_policies, key=lambda item: (item.effective_from, item.created_at))
    return SourcePolicySummary(
        id=policy.id,
        status=policy.status,
        reason=policy.reason,
        allowed_actions=actions_from_raw(policy.allowed_actions),
        denied_actions=actions_from_raw(policy.denied_actions),
        effective_from=policy.effective_from,
    )


def _policy_read(policy: SourcePolicy) -> SourcePolicyRead:
    return SourcePolicyRead(
        id=policy.id,
        source_id=policy.source_id,
        status=policy.status,
        reason=policy.reason,
        allowed_actions=actions_from_raw(policy.allowed_actions),
        denied_actions=actions_from_raw(policy.denied_actions),
        effective_from=policy.effective_from,
        effective_to=policy.effective_to,
        evidence_items=[
            SourcePolicyEvidenceRead.model_validate(evidence) for evidence in policy.evidence_items
        ],
    )


app = create_app()
