import pytest

from app.services.domain import DomainNormalizationError, normalize_domain


def test_normalize_domain_strips_url_parts_and_www() -> None:
    assert normalize_domain("HTTPS://www.LinkedIn.com:443/jobs?keywords=python") == "linkedin.com"
    assert normalize_domain("www.Example.CO.UK/path?q=1") == "example.co.uk"


@pytest.mark.parametrize(
    "raw_domain",
    ["", "https://", "bad_domain.example", "example..com", "localhost:8000"],
)
def test_normalize_domain_rejects_empty_or_invalid_domains(raw_domain: str) -> None:
    with pytest.raises(DomainNormalizationError):
        normalize_domain(raw_domain)
