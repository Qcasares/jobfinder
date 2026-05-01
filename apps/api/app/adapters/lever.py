from app.adapters.base import RawJobPayload
from app.adapters.common import (
    as_mapping,
    normalize_employment_type,
    normalize_remote_type,
    object_list,
    parse_date,
    parse_json_object,
    parse_salary_text,
    payload_hash,
    split_locations,
    text,
)
from app.adapters.schema import RawJobPosting


class LeverAdapter:
    source = "lever"
    extraction_method = "official_api_fixture"

    def parse(self, payload: RawJobPayload, *, source_url: str) -> list[RawJobPosting]:
        data = parse_json_object(payload)
        digest = payload_hash(payload)
        postings: list[RawJobPosting] = []
        for posting in object_list(data.get("postings")):
            categories = as_mapping(posting.get("categories"))
            locations = split_locations(categories.get("location"))
            salary_min, salary_max, salary_currency = _salary_from_lists(posting)
            postings.append(
                RawJobPosting(
                    source=self.source,
                    source_url=text(posting.get("hostedUrl"), default=source_url),
                    application_url=text(
                        posting.get("applyUrl"),
                        default=text(posting.get("hostedUrl"), default=source_url),
                    ),
                    external_id=text(posting.get("id")),
                    title=text(posting.get("text")),
                    company=text(posting.get("company")),
                    locations=locations,
                    remote_type=normalize_remote_type(
                        posting.get("workplaceType"),
                        locations=locations,
                    ),
                    employment_type=normalize_employment_type(categories.get("commitment")),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency,
                    posted_date=parse_date(posting.get("createdAt")),
                    valid_through=parse_date(posting.get("validThrough")),
                    extraction_method=self.extraction_method,
                    raw_payload_hash=digest,
                )
            )
        return postings


def _salary_from_lists(posting: dict[str, object]) -> tuple[int | None, int | None, str | None]:
    for item in object_list(posting.get("lists")):
        label = text(item.get("text")).casefold()
        if "compensation" in label or "salary" in label:
            return parse_salary_text(item.get("content"))
    return (None, None, None)
