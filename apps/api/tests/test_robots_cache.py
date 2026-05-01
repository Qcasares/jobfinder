from http import HTTPStatus

import httpx

from app.schemas.policy import PolicyAction
from app.services.robots import RobotsCacheService


def test_robots_cache_fetches_normalized_domain_once_and_checks_path_rules() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            HTTPStatus.OK,
            text="User-agent: *\nAllow: /jobs\nDisallow: /private\n",
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = RobotsCacheService(client=client)

    private_result = service.check_read_allowed(
        domain="HTTPS://www.Example.com:443/search",
        path="/private/job-1",
        action=PolicyAction.DISCOVER,
    )
    public_result = service.check_read_allowed(
        domain="example.com",
        path="/jobs/job-2",
        action=PolicyAction.EXTRACT,
    )

    assert private_result.domain == "example.com"
    assert private_result.status_code == HTTPStatus.OK
    assert private_result.allowed is False
    assert public_result.allowed is True
    assert calls == ["https://example.com/robots.txt"]
