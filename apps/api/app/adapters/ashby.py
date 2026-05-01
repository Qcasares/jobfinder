from app.adapters.base import RawJobPayload
from app.adapters.common import (
    normalize_employment_type,
    normalize_remote_type,
    object_list,
    parse_date,
    parse_json_object,
    parse_salary_mapping,
    payload_hash,
    split_locations,
    text,
)
from app.adapters.schema import RawJobPosting


class AshbyAdapter:
    source = "ashby"
    extraction_method = "official_api_fixture"

    def parse(self, payload: RawJobPayload, *, source_url: str) -> list[RawJobPosting]:
        data = parse_json_object(payload)
        digest = payload_hash(payload)
        postings: list[RawJobPosting] = []
        for job in object_list(data.get("jobs")):
            locations = split_locations(job.get("location"))
            salary_min, salary_max, salary_currency = parse_salary_mapping(job.get("compensation"))
            postings.append(
                RawJobPosting(
                    source=self.source,
                    source_url=text(job.get("jobUrl"), default=source_url),
                    application_url=text(
                        job.get("applyUrl"),
                        default=text(job.get("jobUrl"), default=source_url),
                    ),
                    external_id=text(job.get("id")),
                    title=text(job.get("title")),
                    company=text(job.get("companyName")),
                    locations=locations,
                    remote_type=normalize_remote_type(job.get("isRemote"), locations=locations),
                    employment_type=normalize_employment_type(job.get("employmentType")),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency,
                    posted_date=parse_date(job.get("publishedDate")),
                    valid_through=parse_date(job.get("validThrough")),
                    extraction_method=self.extraction_method,
                    raw_payload_hash=digest,
                )
            )
        return postings
