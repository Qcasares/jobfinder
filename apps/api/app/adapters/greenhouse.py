from app.adapters.base import RawJobPayload
from app.adapters.common import (
    as_mapping,
    object_list,
    parse_date,
    parse_json_object,
    parse_salary_mapping,
    payload_hash,
    split_locations,
    text,
)
from app.adapters.schema import RawJobPosting


class GreenhouseAdapter:
    source = "greenhouse"
    extraction_method = "official_api_fixture"

    def parse(self, payload: RawJobPayload, *, source_url: str) -> list[RawJobPosting]:
        data = parse_json_object(payload)
        digest = payload_hash(payload)
        postings: list[RawJobPosting] = []
        for job in object_list(data.get("jobs")):
            location = as_mapping(job.get("location"))
            locations = split_locations(location.get("name"))
            salary_min, salary_max, salary_currency = parse_salary_mapping(job.get("salary"))
            postings.append(
                RawJobPosting(
                    source=self.source,
                    source_url=text(job.get("absolute_url"), default=source_url),
                    application_url=text(
                        job.get("apply_url"),
                        default=text(job.get("absolute_url")),
                    ),
                    external_id=text(job.get("id")),
                    title=text(job.get("title")),
                    company=text(job.get("company")),
                    locations=locations,
                    remote_type="remote" if job.get("remote") is True else "onsite",
                    employment_type=_metadata_value(job, "Employment Type"),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency,
                    posted_date=parse_date(job.get("updated_at")),
                    valid_through=parse_date(job.get("valid_through")),
                    extraction_method=self.extraction_method,
                    raw_payload_hash=digest,
                )
            )
        return postings


def _metadata_value(job: dict[str, object], name: str) -> str | None:
    for item in object_list(job.get("metadata")):
        if text(item.get("name")).casefold() == name.casefold():
            raw_value = text(item.get("value"))
            return raw_value.replace("-", "_").casefold() if raw_value else None
    return None
