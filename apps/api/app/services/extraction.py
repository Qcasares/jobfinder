from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

from app.adapters import RawJobPosting
from app.schemas.audit import JsonValue
from app.schemas.extraction import ExtractedJobPosting, FieldProvenance, RemoteType

CANONICAL_FIELDS = (
    "source_url",
    "application_url",
    "title",
    "company",
    "locations",
    "remote_type",
    "salary_min",
    "salary_max",
    "salary_currency",
    "employment_type",
    "posted_date",
    "valid_through",
    "required_skills",
    "preferred_skills",
    "responsibilities",
    "qualifications",
    "extraction_confidence",
)

REVIEW_CONFIDENCE_THRESHOLD = 0.8
_KNOWN_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD"}
_REMOTE_VALUES: dict[str, RemoteType] = {
    "remote": "remote",
    "telecommute": "remote",
    "telecommuting": "remote",
    "hybrid": "hybrid",
    "onsite": "onsite",
    "on_site": "onsite",
    "office": "onsite",
    "in_office": "onsite",
}
_BROAD_LOCATION_WORDS = {
    "north america",
    "united states",
    "usa",
    "us",
    "canada",
    "europe",
    "emea",
    "americas",
    "global",
}
_SKILL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("AWS", r"\baws\b|\bamazon web services\b"),
    ("Azure", r"\bazure\b"),
    ("Data Science", r"\bdata science\b"),
    ("Docker", r"\bdocker\b"),
    ("FastAPI", r"\bfastapi\b"),
    ("GCP", r"\bgcp\b|\bgoogle cloud\b"),
    ("JavaScript", r"\bjavascript\b"),
    ("Kubernetes", r"\bkubernetes\b|\bk8s\b"),
    ("PostgreSQL", r"\bpostgresql\b|\bpostgres\b"),
    ("Python", r"\bpython\b"),
    ("React", r"\breact\b"),
    ("SQL", r"\bsql\b"),
    ("TypeScript", r"\btypescript\b"),
)
_PREFERRED_MARKERS = ("nice to have", "preferred", "bonus", "plus")


def extract_job_posting(
    raw: RawJobPosting,
    *,
    description_text: str | None = None,
    responsibilities_text: str | None = None,
    qualifications_text: str | None = None,
    confidence_threshold: float = REVIEW_CONFIDENCE_THRESHOLD,
) -> ExtractedJobPosting:
    provenance: dict[str, FieldProvenance] = {}
    review_reasons: list[str] = []
    method = raw.extraction_method or "adapter"

    source_url = _required_text(raw.source_url, "source_url", method, provenance, review_reasons)
    application_url = _required_text(
        raw.application_url, "application_url", method, provenance, review_reasons
    )
    title = _required_text(raw.title, "title", method, provenance, review_reasons)
    company = _required_text(raw.company, "company", method, provenance, review_reasons)
    locations = _normalize_locations(raw.locations, method, provenance)
    remote_type = _normalize_remote_type(raw.remote_type, locations, method, provenance)
    salary_min, salary_max, salary_currency = _normalize_salary(raw, method, provenance)
    employment_type = _optional_text(raw.employment_type, "employment_type", method, provenance)
    posted_date = _date_field(raw.posted_date, "posted_date", method, provenance)
    valid_through = _date_field(raw.valid_through, "valid_through", method, provenance)
    responsibilities = _optional_body_text(
        responsibilities_text, "responsibilities", provenance
    )
    qualifications = _optional_body_text(qualifications_text, "qualifications", provenance)
    required_skills, preferred_skills = _extract_skills(
        description_text=description_text,
        responsibilities_text=responsibilities_text,
        qualifications_text=qualifications_text,
        provenance=provenance,
    )

    for field_name in CANONICAL_FIELDS:
        if field_name == "extraction_confidence":
            continue
        if provenance[field_name].confidence < confidence_threshold:
            note = provenance[field_name].note or f"{field_name} confidence is low"
            if note not in review_reasons:
                review_reasons.append(note)

    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        review_reasons.append("salary range is invalid")

    extraction_confidence = min(
        provenance[field_name].confidence
        for field_name in CANONICAL_FIELDS
        if field_name != "extraction_confidence"
    )
    provenance["extraction_confidence"] = _provenance(
        "extraction_confidence",
        source="aggregate",
        method="deterministic_normalization",
        confidence=extraction_confidence,
        raw_value=None,
        normalized_value=extraction_confidence,
        note="minimum confidence across canonical fields",
    )
    requires_review = bool(review_reasons) or extraction_confidence < confidence_threshold

    return ExtractedJobPosting(
        source_url=source_url,
        application_url=application_url,
        title=title,
        company=company,
        locations=locations,
        remote_type=remote_type,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        employment_type=employment_type,
        posted_date=posted_date,
        valid_through=valid_through,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        responsibilities=responsibilities,
        qualifications=qualifications,
        extraction_confidence=extraction_confidence,
        field_provenance=provenance,
        requires_review=requires_review,
        review_status="needs_review" if requires_review else "ready",
        review_reasons=tuple(dict.fromkeys(review_reasons)),
    )


def _required_text(
    value: object,
    field_name: str,
    method: str,
    provenance: dict[str, FieldProvenance],
    review_reasons: list[str],
) -> str:
    normalized = _clean_text(value)
    confidence = 1.0 if normalized else 0.0
    note = "" if normalized else f"{field_name} is missing"
    if note:
        review_reasons.append(note)
    provenance[field_name] = _provenance(
        field_name,
        source="structured_adapter",
        method=method,
        confidence=confidence,
        raw_value=_jsonify(value),
        normalized_value=normalized,
        note=note,
    )
    return normalized


def _optional_text(
    value: object,
    field_name: str,
    method: str,
    provenance: dict[str, FieldProvenance],
) -> str | None:
    normalized = _clean_text(value) or None
    provenance[field_name] = _provenance(
        field_name,
        source="structured_adapter",
        method=method,
        confidence=1.0,
        raw_value=_jsonify(value),
        normalized_value=normalized,
        note="" if normalized is not None else "optional field missing in source",
    )
    return normalized


def _optional_body_text(
    value: object,
    field_name: str,
    provenance: dict[str, FieldProvenance],
) -> str | None:
    normalized = _clean_text(value) or None
    provenance[field_name] = _provenance(
        field_name,
        source="text_fields",
        method="deterministic_text_cleanup",
        confidence=1.0,
        raw_value=_jsonify(value),
        normalized_value=normalized,
        note="" if normalized is not None else "optional text not provided",
    )
    return normalized


def _date_field(
    value: date | None,
    field_name: str,
    method: str,
    provenance: dict[str, FieldProvenance],
) -> date | None:
    provenance[field_name] = _provenance(
        field_name,
        source="structured_adapter",
        method=method,
        confidence=1.0,
        raw_value=_jsonify(value),
        normalized_value=_jsonify(value),
        note="" if value is not None else "optional date missing in source",
    )
    return value


def _normalize_locations(
    raw_locations: Iterable[str],
    method: str,
    provenance: dict[str, FieldProvenance],
) -> tuple[str, ...]:
    locations = _dedupe_clean_strings(raw_locations)
    if not locations:
        locations = ("unknown",)
        confidence = 0.5
        note = "locations missing; classified as unknown"
    else:
        confidence = 1.0
        note = ""
    provenance["locations"] = _provenance(
        "locations",
        source="structured_adapter",
        method=method,
        confidence=confidence,
        raw_value=list(raw_locations),
        normalized_value=list(locations),
        note=note,
    )
    return locations


def _normalize_remote_type(
    raw_remote_type: object,
    locations: tuple[str, ...],
    method: str,
    provenance: dict[str, FieldProvenance],
) -> RemoteType:
    raw = _clean_text(raw_remote_type)
    normalized_raw = raw.casefold().replace("-", "_").replace(" ", "_")
    if normalized_raw in _REMOTE_VALUES:
        remote_type = _REMOTE_VALUES[normalized_raw]
        confidence = 1.0
        source = "structured_adapter"
        note = ""
    else:
        joined_locations = " ".join(locations).casefold()
        if "hybrid" in joined_locations:
            remote_type = "hybrid"
            confidence = 0.85
            note = "remote_type inferred from hybrid location text"
        elif "remote" in joined_locations:
            remote_type = "remote"
            confidence = 0.85
            note = "remote_type inferred from remote location text"
        elif _looks_like_specific_location(locations):
            remote_type = "onsite"
            confidence = 0.75
            note = "remote_type inferred from specific location text"
        else:
            remote_type = "unknown"
            confidence = 0.5
            note = "remote_type could not be determined"
        source = "location_text"
    provenance["remote_type"] = _provenance(
        "remote_type",
        source=source,
        method=method if source == "structured_adapter" else "deterministic_location_heuristic",
        confidence=confidence,
        raw_value={"remote_type": _jsonify(raw_remote_type), "locations": list(locations)},
        normalized_value=remote_type,
        note=note,
    )
    return remote_type


def _normalize_salary(
    raw: RawJobPosting,
    method: str,
    provenance: dict[str, FieldProvenance],
) -> tuple[int | None, int | None, str | None]:
    salary_min = raw.salary_min
    salary_max = raw.salary_max
    currency = _clean_text(raw.salary_currency).upper() or None
    confidence = 1.0
    note = ""

    if salary_min is None and salary_max is None:
        currency = None
        note = "salary missing in source; preserved as None"
    elif currency is not None and currency not in _KNOWN_CURRENCIES:
        currency = None
        confidence = 0.6
        note = "salary currency was invalid"
    elif (
        salary_min is not None
        and salary_max is not None
        and salary_min > salary_max
    ):
        salary_min, salary_max = salary_max, salary_min
        confidence = 0.6
        note = "salary range was reversed"
    elif (salary_min is not None and salary_min < 0) or (salary_max is not None and salary_max < 0):
        salary_min = None
        salary_max = None
        currency = None
        confidence = 0.4
        note = "salary range contained a negative value"

    raw_value = {
        "salary_min": raw.salary_min,
        "salary_max": raw.salary_max,
        "salary_currency": _jsonify(raw.salary_currency),
    }
    for field_name, value in (
        ("salary_min", salary_min),
        ("salary_max", salary_max),
        ("salary_currency", currency),
    ):
        provenance[field_name] = _provenance(
            field_name,
            source="structured_adapter",
            method=method,
            confidence=confidence,
            raw_value=raw_value,
            normalized_value=value,
            note=note,
        )
    return salary_min, salary_max, currency


def _extract_skills(
    *,
    description_text: str | None,
    responsibilities_text: str | None,
    qualifications_text: str | None,
    provenance: dict[str, FieldProvenance],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    required_text = "\n".join(
        text
        for text in (_clean_text(responsibilities_text), _clean_text(qualifications_text))
        if text
    )
    preferred_text = "\n".join(_preferred_sentences(_clean_text(description_text)))
    if "data science" in _clean_text(description_text).casefold():
        preferred_text = f"{preferred_text}\nData Science"
    required_skills = _find_skills(required_text)
    preferred_skills = tuple(
        skill for skill in _find_skills(preferred_text) if skill not in set(required_skills)
    )
    raw_value = {
        "description_text": _jsonify(description_text),
        "responsibilities_text": _jsonify(responsibilities_text),
        "qualifications_text": _jsonify(qualifications_text),
    }
    provenance["required_skills"] = _provenance(
        "required_skills",
        source="text_fields",
        method="deterministic_keyword_extraction",
        confidence=1.0,
        raw_value=raw_value,
        normalized_value=list(required_skills),
        note="small local keyword set; no LLM calls",
    )
    provenance["preferred_skills"] = _provenance(
        "preferred_skills",
        source="text_fields",
        method="deterministic_keyword_extraction",
        confidence=1.0,
        raw_value=raw_value,
        normalized_value=list(preferred_skills),
        note="small local keyword set; no LLM calls",
    )
    return required_skills, preferred_skills


def _find_skills(text: str) -> tuple[str, ...]:
    found = [
        skill
        for skill, pattern in _SKILL_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    return tuple(sorted(found))


def _preferred_sentences(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return tuple(
        sentence
        for sentence in sentences
        if any(marker in sentence.casefold() for marker in _PREFERRED_MARKERS)
    )


def _dedupe_clean_strings(values: Iterable[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = _clean_text(value)
        if not candidate:
            continue
        key = candidate.casefold()
        if key in seen:
            continue
        cleaned.append(candidate)
        seen.add(key)
    return tuple(cleaned)


def _looks_like_specific_location(locations: tuple[str, ...]) -> bool:
    for location in locations:
        normalized = location.casefold().strip()
        if normalized == "unknown" or normalized in _BROAD_LOCATION_WORDS:
            continue
        if "," in location:
            return True
        if any(
            word in normalized for word in ("office", "hq", "headquarters", "on-site", "onsite")
        ):
            return True
    return False


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _provenance(
    field_name: str,
    *,
    source: str,
    method: str,
    confidence: float,
    raw_value: JsonValue,
    normalized_value: JsonValue,
    note: str = "",
) -> FieldProvenance:
    return FieldProvenance(
        field_name=field_name,
        source=source,
        extraction_method=method,
        confidence=confidence,
        raw_value=raw_value,
        normalized_value=normalized_value,
        note=note,
    )


def _jsonify(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonify(item) for item in value]
    return str(value)
