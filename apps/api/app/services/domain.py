from urllib.parse import urlsplit


class DomainNormalizationError(ValueError):
    """Raised when a source domain cannot be normalized into a valid hostname."""


def normalize_domain(raw_domain: str) -> str:
    candidate = raw_domain.strip().lower()
    if not candidate:
        raise DomainNormalizationError("domain cannot be empty")

    parse_target = candidate if "://" in candidate else f"//{candidate}"
    parsed = urlsplit(parse_target)
    try:
        _ = parsed.port
    except ValueError as exc:
        raise DomainNormalizationError(f"domain has an invalid port: {raw_domain}") from exc

    hostname = parsed.hostname
    if hostname is None:
        raise DomainNormalizationError(f"domain is invalid: {raw_domain}")

    normalized = hostname.removeprefix("www.").rstrip(".")
    if not _is_valid_domain(normalized):
        raise DomainNormalizationError(f"domain is invalid: {raw_domain}")
    return normalized


def _is_valid_domain(domain: str) -> bool:
    if len(domain) > 253 or "." not in domain:
        return False

    labels = domain.split(".")
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if not all(
            character.isascii() and (character.isalnum() or character == "-") for character in label
        ):
            return False
    return True
