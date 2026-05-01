from app.adapters.base import RawJobPayload
from app.adapters.common import (
    JsonMap,
    as_mapping,
    first_text,
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


class JsonLdAdapter:
    source = "json-ld"
    extraction_method = "structured_data_fixture"

    def parse(self, payload: RawJobPayload, *, source_url: str) -> list[RawJobPosting]:
        data = parse_json_object(payload)
        digest = payload_hash(payload)
        postings: list[RawJobPosting] = []
        for job in _job_postings(data):
            organization = as_mapping(job.get("hiringOrganization"))
            identifier = as_mapping(job.get("identifier"))
            salary = as_mapping(job.get("baseSalary"))
            salary_min, salary_max, salary_currency = parse_salary_mapping(
                as_mapping(salary.get("value"))
            )
            salary_currency = salary_currency or text(salary.get("currency")).upper() or None
            locations = _locations(job)
            postings.append(
                RawJobPosting(
                    source=self.source,
                    source_url=text(job.get("url"), default=source_url),
                    application_url=first_text(
                        job.get("applicationContact"),
                        job.get("url"),
                        source_url,
                    ),
                    external_id=first_text(identifier.get("value"), job.get("url"), source_url),
                    title=text(job.get("title")),
                    company=text(organization.get("name")),
                    locations=locations,
                    remote_type=normalize_remote_type(
                        job.get("jobLocationType"),
                        locations=locations,
                    ),
                    employment_type=normalize_employment_type(job.get("employmentType")),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency,
                    posted_date=parse_date(job.get("datePosted")),
                    valid_through=parse_date(job.get("validThrough")),
                    extraction_method=self.extraction_method,
                    raw_payload_hash=digest,
                )
            )
        return postings


def _job_postings(data: JsonMap) -> list[JsonMap]:
    if data.get("@type") == "JobPosting":
        return [data]
    graph = data.get("@graph")
    return [item for item in object_list(graph) if item.get("@type") == "JobPosting"]


def _locations(job: JsonMap) -> tuple[str, ...]:
    if text(job.get("jobLocationType")).casefold() == "telecommute":
        requirements = as_mapping(job.get("applicantLocationRequirements"))
        return split_locations(requirements.get("name") or "Remote")
    locations = object_list(job.get("jobLocation"))
    labels: list[str] = []
    for location in locations:
        address = as_mapping(location.get("address"))
        labels.append(
            first_text(
                address.get("streetAddress"),
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            )
        )
    return split_locations(labels)
