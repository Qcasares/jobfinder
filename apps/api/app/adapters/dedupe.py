import re
from urllib.parse import urlsplit, urlunsplit

from app.adapters.schema import RawJobPosting


def dedupe_raw_job_postings(postings: list[RawJobPosting]) -> list[RawJobPosting]:
    seen_urls: set[str] = set()
    seen_signatures: set[tuple[str, str, tuple[str, ...]]] = set()
    deduped: list[RawJobPosting] = []

    for posting in postings:
        url_key = _canonical_url(posting.source_url)
        signature_key = _signature(posting)
        if url_key in seen_urls or signature_key in seen_signatures:
            continue
        deduped.append(posting)
        seen_urls.add(url_key)
        seen_signatures.add(signature_key)

    return deduped


def _canonical_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.casefold()
    netloc = parsed.netloc.casefold()
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def _signature(posting: RawJobPosting) -> tuple[str, str, tuple[str, ...]]:
    return (
        _normalize_text(posting.company),
        _normalize_text(posting.title),
        tuple(sorted(_normalize_text(location) for location in posting.locations)),
    )


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())
