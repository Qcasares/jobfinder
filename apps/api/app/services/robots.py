from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus

import httpx

from app.schemas.policy import PolicyAction
from app.services.domain import normalize_domain

READ_ACTIONS = {PolicyAction.DISCOVER, PolicyAction.EXTRACT}


@dataclass(frozen=True)
class RobotsCheckResult:
    domain: str
    status_code: int
    fetched_at: datetime
    allowed: bool


@dataclass(frozen=True)
class CachedRobots:
    status_code: int
    fetched_at: datetime
    body: str


class RobotsCacheService:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = client or httpx.Client(transport=transport, timeout=5.0)
        self._cache: dict[str, CachedRobots] = {}

    def check_read_allowed(
        self,
        *,
        domain: str,
        path: str,
        action: PolicyAction,
    ) -> RobotsCheckResult:
        normalized_domain = normalize_domain(domain)
        cached = self._get_or_fetch(normalized_domain)
        allowed = action in READ_ACTIONS and self._path_allowed(
            cached.status_code,
            cached.body,
            path,
        )
        return RobotsCheckResult(
            domain=normalized_domain,
            status_code=cached.status_code,
            fetched_at=cached.fetched_at,
            allowed=allowed,
        )

    def _get_or_fetch(self, domain: str) -> CachedRobots:
        cached = self._cache.get(domain)
        if cached is not None:
            return cached

        response = self._client.get(f"https://{domain}/robots.txt")
        fetched = CachedRobots(
            status_code=response.status_code,
            fetched_at=datetime.now(UTC),
            body=response.text,
        )
        self._cache[domain] = fetched
        return fetched

    @staticmethod
    def _path_allowed(status_code: int, body: str, path: str) -> bool:
        if status_code == HTTPStatus.NOT_FOUND:
            return True
        if status_code < 200 or status_code >= 300:
            return False

        rules = _parse_robots_rules(body)
        if not rules:
            return True

        matched: tuple[int, bool] | None = None
        for prefix, allowed in rules:
            if prefix and path.startswith(prefix):
                score = len(prefix)
                if matched is None or score > matched[0] or (score == matched[0] and allowed):
                    matched = (score, allowed)
        return True if matched is None else matched[1]


def _parse_robots_rules(body: str) -> list[tuple[str, bool]]:
    active_for_all = False
    rules: list[tuple[str, bool]] = []

    for raw_line in body.splitlines():
        line = raw_line.split("#", maxsplit=1)[0].strip()
        if not line or ":" not in line:
            continue

        field, value = [part.strip() for part in line.split(":", maxsplit=1)]
        field = field.lower()
        if field == "user-agent":
            active_for_all = value == "*"
            continue

        if not active_for_all:
            continue
        if field == "allow":
            rules.append((value, True))
        if field == "disallow" and value:
            rules.append((value, False))

    return rules
