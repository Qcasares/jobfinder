import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from html import unescape
from typing import Any, cast

from app.adapters.base import RawJobPayload

type JsonMap = dict[str, Any]
type Salary = tuple[int | None, int | None, str | None]

_CURRENCY_SYMBOLS = {"$": "USD", "\N{POUND SIGN}": "GBP", "\N{EURO SIGN}": "EUR"}
_KNOWN_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD"}


def payload_hash(payload: RawJobPayload) -> str:
    if isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        raw = payload.encode()
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def parse_json_object(payload: RawJobPayload) -> JsonMap:
    if isinstance(payload, bytes):
        decoded = payload.decode()
        parsed = json.loads(decoded)
    elif isinstance(payload, str):
        parsed = json.loads(payload)
    else:
        parsed = payload
    if not isinstance(parsed, dict):
        raise ValueError("adapter fixture payload must be a JSON object")
    return parsed


def object_list(value: object) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [cast(JsonMap, item) for item in value if isinstance(item, dict)]


def as_mapping(value: object) -> JsonMap:
    if isinstance(value, dict):
        return cast(JsonMap, value)
    return {}


def text(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def first_text(*values: object, default: str = "") -> str:
    for value in values:
        candidate = text(value)
        if candidate:
            return candidate
    return default


def parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, int | float):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC).date()
    raw = text(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None


def split_locations(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list | tuple):
        locations: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                locations.append(
                    first_text(
                        item.get("location_str"),
                        item.get("name"),
                        item.get("city"),
                    )
                )
            else:
                locations.append(text(item))
        return clean_tuple(locations)
    raw = text(value)
    if not raw:
        return ()
    if ";" in raw:
        parts = raw.split(";")
    elif "\n" in raw:
        parts = raw.splitlines()
    else:
        parts = [raw]
    return clean_tuple(parts)


def clean_tuple(values: Iterable[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = unescape(value).strip()
        if not candidate:
            continue
        key = candidate.casefold()
        if key in seen:
            continue
        cleaned.append(candidate)
        seen.add(key)
    return tuple(cleaned)


def join_location_parts(*values: object) -> str:
    return ", ".join(part for part in (text(value) for value in values) if part)


def normalize_employment_type(value: object) -> str | None:
    raw = text(value).casefold().replace("-", "_").replace(" ", "_")
    if not raw:
        return None
    mapping = {
        "full_time": "full_time",
        "fulltime": "full_time",
        "part_time": "part_time",
        "parttime": "part_time",
        "contractor": "contract",
        "contract": "contract",
        "temporary": "temporary",
        "intern": "internship",
        "internship": "internship",
    }
    return mapping.get(raw, raw)


def normalize_remote_type(value: object, *, locations: tuple[str, ...] = ()) -> str | None:
    if isinstance(value, bool):
        return "remote" if value else "onsite"
    raw = text(value).casefold().replace("-", "_").replace(" ", "_")
    if raw in {"remote", "telecommute", "telecommuting"}:
        return "remote"
    if raw in {"hybrid"}:
        return "hybrid"
    if raw in {"onsite", "on_site", "office"}:
        return "onsite"
    if any("remote" in location.casefold() for location in locations):
        return "remote"
    return None


def parse_salary_text(value: object) -> Salary:
    raw = text(value)
    if not raw:
        return (None, None, None)
    currency = None
    for symbol, symbol_currency in _CURRENCY_SYMBOLS.items():
        if symbol in raw:
            currency = symbol_currency
            break
    for candidate in _KNOWN_CURRENCIES:
        if re.search(rf"\b{candidate}\b", raw, flags=re.IGNORECASE):
            currency = candidate
            break
    numbers = [int(number.replace(",", "")) for number in re.findall(r"\d[\d,]*", raw)]
    if not numbers:
        return (None, None, currency)
    salary_min = numbers[0]
    salary_max = numbers[1] if len(numbers) > 1 else numbers[0]
    return (salary_min, salary_max, currency)


def parse_salary_mapping(value: object) -> Salary:
    if not isinstance(value, dict):
        return (None, None, None)
    data = cast(JsonMap, value)
    salary_min = int_or_none(first_present(data, "min", "minValue", "minimum"))
    salary_max = int_or_none(first_present(data, "max", "maxValue", "maximum"))
    currency = text(first_present(data, "currency", "currencyCode")).upper() or None
    if salary_min is None and salary_max is None:
        return (None, None, currency)
    return (salary_min, salary_max, currency)


def first_present(data: Mapping[str, Any], *keys: str) -> object:
    for key in keys:
        if key in data:
            return data[key]
    return None


def int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None
