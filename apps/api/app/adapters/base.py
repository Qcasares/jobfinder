from typing import Any, Protocol

from app.adapters.schema import RawJobPosting

type RawJobPayload = str | bytes | dict[str, Any]


class JobSourceAdapter(Protocol):
    source: str
    extraction_method: str

    def parse(self, payload: RawJobPayload, *, source_url: str) -> list[RawJobPosting]:
        """Parse an already-recorded fixture payload into canonical raw postings."""
