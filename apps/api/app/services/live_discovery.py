from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from sqlalchemy.orm import Session

from app.adapters import JsonLdAdapter, StaticHtmlAdapter
from app.config import Settings
from app.schemas.audit import ActorType, JsonValue
from app.schemas.live_discovery import (
    LiveDiscoveryFailure,
    LiveDiscoveryRequest,
    LiveDiscoveryRun,
    LiveDiscoveryStatus,
    LiveSearchDiscoveryRequest,
)
from app.schemas.manual_handoff import ManualHandoffCreate, ManualHandoffTrigger
from app.schemas.policy import PolicyAction, PolicyDecision
from app.schemas.review import ReviewQueueItem
from app.services.audit import AuditEventService
from app.services.domain import normalize_domain
from app.services.manual_handoff import ManualHandoffService
from app.services.review_queue import ReviewQueueService
from app.services.source_registry import SourceRegistryService


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    status_code: int
    content_type: str
    body: bytes


FetchFunction = Callable[[str], FetchResult]


@dataclass(frozen=True)
class StopCondition:
    trigger_type: ManualHandoffTrigger
    detail: str


class LiveDiscoveryService:
    def __init__(
        self,
        session: Session | None = None,
        *,
        settings: Settings,
        audit_service: AuditEventService | None = None,
        fetcher: FetchFunction | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._audit_service = audit_service
        self._fetcher = fetcher or self._default_fetch
        self._runs: dict[str, LiveDiscoveryRun] = {}
        self._search_runs: dict[str, LiveDiscoveryRun] = {}
        self._review_items: list[ReviewQueueItem] = []

    def run(
        self,
        request: LiveDiscoveryRequest,
        *,
        session: Session | None = None,
    ) -> LiveDiscoveryRun:
        active_session = session or self._session
        if active_session is None:
            raise ValueError("session is required")

        run_id = str(uuid4())
        url = str(request.url)
        source_domain = self._source_domain(url, request.source_domain)
        self._audit(
            "live_discovery.requested",
            run_id,
            {
                "url": url,
                "source_domain": source_domain,
                "requested_by": request.requested_by,
            },
        )

        if not self._settings.live_discovery_enabled:
            return self._deny(
                run_id,
                request,
                source_domain,
                reason="live_discovery_disabled",
                detail="Live discovery is disabled by runtime configuration.",
            )

        invalid_detail = self._invalid_url_detail(url)
        if invalid_detail is not None:
            return self._deny(
                run_id,
                request,
                source_domain,
                reason="invalid_url",
                detail=invalid_detail,
            )

        registry = SourceRegistryService(
            active_session,
            audit_service=self._audit_service or AuditEventService(session=active_session),
        )
        discover = registry.evaluate_action(domain=source_domain, action=PolicyAction.DISCOVER)
        extract = registry.evaluate_action(domain=source_domain, action=PolicyAction.EXTRACT)
        denied = _first_denied(discover, extract)
        if denied is not None:
            return self._deny(
                run_id,
                request,
                source_domain,
                reason="source_policy_denied",
                detail=denied.reason,
            )

        try:
            fetched = self._fetcher(url)
        except Exception as exc:
            return self._fail(
                run_id,
                request,
                source_domain,
                reason="fetch_failed",
                detail=str(exc),
            )

        final_domain = self._source_domain(fetched.final_url, None)
        if final_domain != source_domain:
            return self._deny(
                run_id,
                request,
                source_domain,
                reason="redirect_domain_mismatch",
                detail=f"Final URL domain {final_domain} does not match {source_domain}.",
                final_url=fetched.final_url,
                fetched_status_code=fetched.status_code,
                content_type=fetched.content_type,
            )
        if fetched.status_code >= 400:
            return self._fail(
                run_id,
                request,
                source_domain,
                reason="fetch_http_error",
                detail=f"Live source returned HTTP {fetched.status_code}.",
                final_url=fetched.final_url,
                fetched_status_code=fetched.status_code,
                content_type=fetched.content_type,
            )

        self._audit(
            "live_discovery.fetched",
            run_id,
            {
                "url": url,
                "final_url": fetched.final_url,
                "status_code": fetched.status_code,
                "content_type": fetched.content_type,
                "bytes": len(fetched.body),
            },
        )
        stop_condition = _detect_stop_condition(fetched.body)
        if stop_condition is not None:
            return self._manual_handoff(
                active_session,
                run_id,
                request,
                source_domain,
                stop_condition,
                final_url=fetched.final_url,
                fetched_status_code=fetched.status_code,
                content_type=fetched.content_type,
            )

        items = self._extract_review_items(fetched, source_url=url)
        if not items:
            return self._fail(
                run_id,
                request,
                source_domain,
                reason="unsupported_content",
                detail="No supported JobPosting JSON-LD or static HTML job payload was found.",
                final_url=fetched.final_url,
                fetched_status_code=fetched.status_code,
                content_type=fetched.content_type,
            )

        self._review_items.extend(items)
        run = LiveDiscoveryRun(
            id=run_id,
            url=url,
            final_url=fetched.final_url,
            source_domain=source_domain,
            requested_by=request.requested_by,
            status=LiveDiscoveryStatus.EXTRACTED,
            fetched_status_code=fetched.status_code,
            content_type=fetched.content_type,
            extracted_count=len(items),
            review_item_ids=tuple(item.id for item in items),
        )
        self._runs[run.id] = run
        self._audit(
            "live_discovery.extracted",
            run_id,
            {
                "extracted_count": len(items),
                "review_item_ids": list(run.review_item_ids),
                "synthetic": False,
            },
        )
        return run

    def get_run(self, run_id: str) -> LiveDiscoveryRun | None:
        return self._runs.get(run_id)

    def discover_search_results(
        self,
        *,
        url: str,
        source_domain: str | None = None,
        requested_by: str = "local-operator",
        max_results: int = 25,
        session: Session | None = None,
    ) -> LiveDiscoveryRun:
        request = LiveSearchDiscoveryRequest(
            url=url,
            source_domain=source_domain,
            requested_by=requested_by,
            max_results=max_results,
        )
        return self.run_search_discovery(request, session=session)

    def run_search_discovery(
        self,
        request: LiveSearchDiscoveryRequest,
        *,
        session: Session | None = None,
    ) -> LiveDiscoveryRun:
        active_session = session or self._session
        if active_session is None:
            raise ValueError("session is required")

        run_id = str(uuid4())
        url = str(request.url)
        source_domain = self._source_domain(url, request.source_domain)
        self._audit(
            "live_search_discovery.requested",
            run_id,
            {
                "url": url,
                "source_domain": source_domain,
                "requested_by": request.requested_by,
                "max_results": request.max_results,
            },
        )

        if not self._settings.live_search_discovery_enabled:
            return self._deny_search(
                run_id,
                request,
                source_domain,
                reason="live_search_discovery_disabled",
                detail="Live search-result discovery is disabled by runtime configuration.",
            )

        invalid_detail = self._invalid_url_detail(url)
        if invalid_detail is not None:
            return self._deny_search(
                run_id,
                request,
                source_domain,
                reason="invalid_url",
                detail=invalid_detail,
            )

        registry = SourceRegistryService(
            active_session,
            audit_service=self._audit_service or AuditEventService(session=active_session),
        )
        discover = registry.evaluate_action(domain=source_domain, action=PolicyAction.DISCOVER)
        if not discover.allowed:
            return self._deny_search(
                run_id,
                request,
                source_domain,
                reason="source_policy_denied",
                detail=discover.reason,
            )

        try:
            fetched = self._fetcher(url)
        except Exception as exc:
            return self._fail_search(
                run_id,
                request,
                source_domain,
                reason="fetch_failed",
                detail=str(exc),
            )

        final_domain = self._source_domain(fetched.final_url, None)
        if final_domain != source_domain:
            return self._deny_search(
                run_id,
                request,
                source_domain,
                reason="redirect_domain_mismatch",
                detail=f"Final URL domain {final_domain} does not match {source_domain}.",
                final_url=fetched.final_url,
                fetched_status_code=fetched.status_code,
                content_type=fetched.content_type,
            )
        if fetched.status_code >= 400:
            return self._fail_search(
                run_id,
                request,
                source_domain,
                reason="fetch_http_error",
                detail=f"Live source returned HTTP {fetched.status_code}.",
                final_url=fetched.final_url,
                fetched_status_code=fetched.status_code,
                content_type=fetched.content_type,
            )

        stop_condition = _detect_stop_condition(fetched.body)
        if stop_condition is not None:
            return self._manual_handoff_search(
                active_session,
                run_id,
                request,
                source_domain,
                stop_condition,
                final_url=fetched.final_url,
                fetched_status_code=fetched.status_code,
                content_type=fetched.content_type,
            )

        discovered_urls = _discover_job_links(
            fetched.body,
            base_url=fetched.final_url,
            source_domain=source_domain,
            max_results=request.max_results,
        )
        run = LiveDiscoveryRun(
            id=run_id,
            url=url,
            final_url=fetched.final_url,
            source_domain=source_domain,
            requested_by=request.requested_by,
            status=LiveDiscoveryStatus.DISCOVERED,
            fetched_status_code=fetched.status_code,
            content_type=fetched.content_type,
            discovered_count=len(discovered_urls),
            discovered_urls=tuple(discovered_urls),
        )
        self._search_runs[run.id] = run
        self._audit(
            "live_search_discovery.discovered",
            run_id,
            {
                "discovered_count": len(discovered_urls),
                "discovered_urls": list(discovered_urls),
                "source_domain": source_domain,
            },
        )
        return run

    def get_search_run(self, run_id: str) -> LiveDiscoveryRun | None:
        return self._search_runs.get(run_id)

    def review_items(self) -> list[ReviewQueueItem]:
        return list(self._review_items)

    def _extract_review_items(
        self,
        fetched: FetchResult,
        *,
        source_url: str,
    ) -> list[ReviewQueueItem]:
        raw_postings = []
        for payload in _json_ld_payloads(fetched.body):
            raw_postings.extend(JsonLdAdapter().parse(payload, source_url=source_url))
        if not raw_postings:
            try:
                raw_postings.extend(StaticHtmlAdapter().parse(fetched.body, source_url=source_url))
            except Exception:
                raw_postings = []
        synthetic_items = ReviewQueueService(
            fixture_specs=(),
            raw_postings=raw_postings,
        ).list_items()
        return [
            item.model_copy(update={"synthetic": False, "data_origin": "live_extraction"})
            for item in synthetic_items
        ]

    def _default_fetch(self, url: str) -> FetchResult:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "text/html,application/ld+json,application/json;q=0.9",
                "User-Agent": "JobfinderLiveDiscovery/0.1 (+policy-gated)",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._settings.live_discovery_timeout_seconds,
            ) as response:
                body = response.read(self._settings.live_discovery_max_bytes + 1)
                if len(body) > self._settings.live_discovery_max_bytes:
                    raise ValueError("response exceeded live discovery byte limit")
                return FetchResult(
                    final_url=response.geturl(),
                    status_code=response.status,
                    content_type=response.headers.get("content-type", ""),
                    body=body,
                )
        except urllib.error.URLError as exc:
            raise ValueError(str(exc.reason)) from exc

    def _deny(
        self,
        run_id: str,
        request: LiveDiscoveryRequest,
        source_domain: str,
        *,
        reason: str,
        detail: str,
        final_url: str | None = None,
        fetched_status_code: int | None = None,
        content_type: str | None = None,
    ) -> LiveDiscoveryRun:
        return self._complete_with_failure(
            run_id,
            request,
            source_domain,
            status=LiveDiscoveryStatus.DENIED,
            reason=reason,
            detail=detail,
            final_url=final_url,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
        )

    def _fail(
        self,
        run_id: str,
        request: LiveDiscoveryRequest,
        source_domain: str,
        *,
        reason: str,
        detail: str,
        final_url: str | None = None,
        fetched_status_code: int | None = None,
        content_type: str | None = None,
    ) -> LiveDiscoveryRun:
        return self._complete_with_failure(
            run_id,
            request,
            source_domain,
            status=LiveDiscoveryStatus.FAILED,
            reason=reason,
            detail=detail,
            final_url=final_url,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
        )

    def _deny_search(
        self,
        run_id: str,
        request: LiveSearchDiscoveryRequest,
        source_domain: str,
        *,
        reason: str,
        detail: str,
        final_url: str | None = None,
        fetched_status_code: int | None = None,
        content_type: str | None = None,
    ) -> LiveDiscoveryRun:
        return self._complete_search_with_failure(
            run_id,
            request,
            source_domain,
            status=LiveDiscoveryStatus.DENIED,
            reason=reason,
            detail=detail,
            final_url=final_url,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
        )

    def _fail_search(
        self,
        run_id: str,
        request: LiveSearchDiscoveryRequest,
        source_domain: str,
        *,
        reason: str,
        detail: str,
        final_url: str | None = None,
        fetched_status_code: int | None = None,
        content_type: str | None = None,
    ) -> LiveDiscoveryRun:
        return self._complete_search_with_failure(
            run_id,
            request,
            source_domain,
            status=LiveDiscoveryStatus.FAILED,
            reason=reason,
            detail=detail,
            final_url=final_url,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
        )

    def _manual_handoff(
        self,
        session: Session,
        run_id: str,
        request: LiveDiscoveryRequest,
        source_domain: str,
        stop_condition: StopCondition,
        *,
        final_url: str,
        fetched_status_code: int,
        content_type: str,
    ) -> LiveDiscoveryRun:
        record = ManualHandoffService(
            session,
            audit_service=self._audit_service or AuditEventService(session=session),
        ).create_record(
            ManualHandoffCreate(
                url=request.url,
                source_domain=source_domain,
                trigger_type=stop_condition.trigger_type,
                requested_by=request.requested_by,
                detection_detail=stop_condition.detail,
                run_id=run_id,
            )
        )
        return self._complete_with_failure(
            run_id,
            request,
            source_domain,
            status=LiveDiscoveryStatus.DENIED,
            reason="manual_handoff_required",
            detail=stop_condition.detail,
            final_url=final_url,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
            manual_handoff_id=record.id,
        )

    def _manual_handoff_search(
        self,
        session: Session,
        run_id: str,
        request: LiveSearchDiscoveryRequest,
        source_domain: str,
        stop_condition: StopCondition,
        *,
        final_url: str,
        fetched_status_code: int,
        content_type: str,
    ) -> LiveDiscoveryRun:
        record = ManualHandoffService(
            session,
            audit_service=self._audit_service or AuditEventService(session=session),
        ).create_record(
            ManualHandoffCreate(
                url=request.url,
                source_domain=source_domain,
                trigger_type=stop_condition.trigger_type,
                requested_by=request.requested_by,
                detection_detail=stop_condition.detail,
                run_id=run_id,
            )
        )
        return self._complete_search_with_failure(
            run_id,
            request,
            source_domain,
            status=LiveDiscoveryStatus.DENIED,
            reason="manual_handoff_required",
            detail=stop_condition.detail,
            final_url=final_url,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
            manual_handoff_id=record.id,
        )

    def _complete_search_with_failure(
        self,
        run_id: str,
        request: LiveSearchDiscoveryRequest,
        source_domain: str,
        *,
        status: LiveDiscoveryStatus,
        reason: str,
        detail: str,
        final_url: str | None,
        fetched_status_code: int | None,
        content_type: str | None,
        manual_handoff_id: str | None = None,
    ) -> LiveDiscoveryRun:
        run = LiveDiscoveryRun(
            id=run_id,
            url=str(request.url),
            final_url=final_url,
            source_domain=source_domain,
            requested_by=request.requested_by,
            status=status,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
            manual_handoff_id=manual_handoff_id,
            failure=LiveDiscoveryFailure(reason=reason, detail=detail),
        )
        self._search_runs[run.id] = run
        self._audit(
            f"live_search_discovery.{status.value}",
            run_id,
            {
                "reason": reason,
                "detail": detail,
                "source_domain": source_domain,
                "url": str(request.url),
                "manual_handoff_id": manual_handoff_id or "",
            },
        )
        return run

    def _complete_with_failure(
        self,
        run_id: str,
        request: LiveDiscoveryRequest,
        source_domain: str,
        *,
        status: LiveDiscoveryStatus,
        reason: str,
        detail: str,
        final_url: str | None,
        fetched_status_code: int | None,
        content_type: str | None,
        manual_handoff_id: str | None = None,
    ) -> LiveDiscoveryRun:
        run = LiveDiscoveryRun(
            id=run_id,
            url=str(request.url),
            final_url=final_url,
            source_domain=source_domain,
            requested_by=request.requested_by,
            status=status,
            fetched_status_code=fetched_status_code,
            content_type=content_type,
            manual_handoff_id=manual_handoff_id,
            failure=LiveDiscoveryFailure(reason=reason, detail=detail),
        )
        self._runs[run.id] = run
        self._audit(
            f"live_discovery.{status.value}",
            run_id,
            {
                "reason": reason,
                "detail": detail,
                "source_domain": source_domain,
                "url": str(request.url),
                "manual_handoff_id": manual_handoff_id or "",
            },
        )
        return run

    def _audit(self, event_type: str, correlation_id: str, payload: dict[str, JsonValue]) -> None:
        if self._audit_service is None:
            return
        self._audit_service.create_event(
            event_type=event_type,
            actor_type=ActorType.WORKER,
            actor_id="live-discovery-service",
            correlation_id=correlation_id,
            payload=payload,
        )

    @staticmethod
    def _source_domain(url: str, source_domain: str | None) -> str:
        if source_domain:
            return normalize_domain(source_domain)
        parsed = urlparse(url)
        return normalize_domain(parsed.hostname or "")

    @staticmethod
    def _invalid_url_detail(url: str) -> str | None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return "Live discovery only accepts HTTPS URLs."
        if not parsed.hostname:
            return "Live discovery URL must include a host."
        return None


def _first_denied(*decisions: PolicyDecision) -> PolicyDecision | None:
    for decision in decisions:
        if not decision.allowed:
            return decision
    return None


def _json_ld_payloads(body: bytes) -> list[bytes]:
    parser = _JsonLdScriptParser()
    parser.feed(body.decode("utf-8", errors="ignore"))
    payloads: list[bytes] = []
    for raw_script in parser.scripts:
        try:
            parsed = json.loads(raw_script)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    payloads.append(json.dumps(item).encode("utf-8"))
        elif isinstance(parsed, dict):
            payloads.append(json.dumps(parsed).encode("utf-8"))
    return payloads


STOP_CONDITION_MARKERS: tuple[tuple[ManualHandoffTrigger, str, tuple[str, ...]], ...] = (
    (
        "captcha",
        "Manual handoff required: CAPTCHA challenge detected.",
        ("captcha", "recaptcha", "hcaptcha"),
    ),
    (
        "bot_detection",
        "Manual handoff required: bot-detection or automated-traffic control detected.",
        ("bot detection", "automated traffic", "unusual traffic", "checking your browser"),
    ),
    (
        "login_required",
        "Manual handoff required: login-only page detected.",
        ("login required", "sign in", "log in", "create an account"),
    ),
    (
        "access_control",
        "Manual handoff required: access-control or identity check detected.",
        ("access denied", "forbidden", "not authorized", "identity verification"),
    ),
)


def _detect_stop_condition(body: bytes) -> StopCondition | None:
    text = body.decode("utf-8", errors="ignore").casefold()
    for trigger_type, detail, markers in STOP_CONDITION_MARKERS:
        if any(marker in text for marker in markers):
            return StopCondition(trigger_type=trigger_type, detail=detail)
    return None


class _JsonLdScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self._capturing = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        if tag == "script" and attr_map.get("type") == "application/ld+json":
            self._capturing = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capturing:
            self.scripts.append("".join(self._buffer).strip())
            self._capturing = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._buffer.append(data)


def _discover_job_links(
    body: bytes,
    *,
    base_url: str,
    source_domain: str,
    max_results: int,
) -> list[str]:
    parser = _LinkParser()
    parser.feed(body.decode("utf-8", errors="ignore"))
    discovered: list[str] = []
    for href in parser.hrefs:
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme != "https":
            continue
        if normalize_domain(parsed.hostname or "") != source_domain:
            continue
        path = parsed.path.lower()
        if not any(marker in path for marker in ("/job", "/jobs", "/careers", "/positions")):
            continue
        normalized = parsed._replace(fragment="").geturl()
        if normalized not in discovered:
            discovered.append(normalized)
        if len(discovered) >= max_results:
            break
    return discovered


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)
