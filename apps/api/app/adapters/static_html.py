from html.parser import HTMLParser

from app.adapters.base import RawJobPayload
from app.adapters.common import (
    int_or_none,
    normalize_employment_type,
    normalize_remote_type,
    parse_date,
    payload_hash,
    split_locations,
    text,
)
from app.adapters.schema import RawJobPosting


class StaticHtmlAdapter:
    source = "static-html"
    extraction_method = "static_html_fixture"

    def parse(self, payload: RawJobPayload, *, source_url: str) -> list[RawJobPosting]:
        raw_html = payload.decode() if isinstance(payload, bytes) else text(payload)
        parser = _StaticJobParser()
        parser.feed(raw_html)
        digest = payload_hash(payload)
        job = parser.job
        locations = split_locations(parser.locations)
        return [
            RawJobPosting(
                source=self.source,
                source_url=text(job.get("data-source-url"), default=source_url),
                application_url=text(job.get("data-apply-url"), default=source_url),
                external_id=text(job.get("data-job-id")),
                title=text(parser.title),
                company=text(job.get("data-company")),
                locations=locations,
                remote_type=normalize_remote_type(job.get("data-remote-type"), locations=locations),
                employment_type=normalize_employment_type(job.get("data-employment-type")),
                salary_min=int_or_none(job.get("data-salary-min")),
                salary_max=int_or_none(job.get("data-salary-max")),
                salary_currency=text(job.get("data-salary-currency")).upper() or None,
                posted_date=parse_date(job.get("data-posted-date")),
                valid_through=parse_date(job.get("data-valid-through")),
                extraction_method=self.extraction_method,
                raw_payload_hash=digest,
            )
        ]


class _StaticJobParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.job: dict[str, str] = {}
        self.title = ""
        self.locations: list[str] = []
        self._capture_title = False
        self._capture_location = False
        self._in_locations = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        if tag == "article" and attr_map.get("data-job-id"):
            self.job = attr_map
        if tag == "h1" and attr_map.get("class") == "job-title":
            self._capture_title = True
        if tag == "ul" and attr_map.get("class") == "locations":
            self._in_locations = True
        if tag == "li" and self._in_locations:
            self._capture_location = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._capture_title = False
        if tag == "li":
            self._capture_location = False
        if tag == "ul":
            self._in_locations = False

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self._capture_title:
            self.title = value
        if self._capture_location:
            self.locations.append(value)
