"""
Base class for source-specific parsers.

The idea: adding a second source (e.g. Arbeitnow) later should mean writing
ONE new file that implements `map_record`, not touching this file, the
fetcher, or anything downstream. This is the "Source Adapter -> Parser ->
Normalizer -> Validator" box from the architecture diagram, collapsed into
one small class per source.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from models import Job

REQUIRED_FIELDS = ("title", "company", "url")


class ValidationError(Exception):
    """Raised when a raw record can't become a valid Job."""

    def __init__(self, reason: str, raw_record: Dict[str, Any]):
        self.reason = reason
        self.raw_record = raw_record
        super().__init__(reason)


def clean_str(value: Any) -> "str | None":
    """Trim whitespace; treat empty/None/non-string junk as missing."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    return value or None


class SourceParser(ABC):
    #: Set by subclasses, e.g. "Remotive"
    SOURCE_NAME: str = "unknown"

    @abstractmethod
    def map_record(self, raw: Dict[str, Any]) -> Job:
        """
        Convert ONE raw source record into a Job.
        Must raise ValidationError if required fields are missing/invalid.
        Subclasses implement only this method.
        """
        raise NotImplementedError

    def parse_many(
        self, raw_jobs: List[Dict[str, Any]]
    ) -> Tuple[List[Job], List[Dict[str, Any]]]:
        """
        Shared loop: try to map every raw record, collect successes and
        failures separately. Never raises - bad records are reported,
        not dropped silently.
        """
        jobs: List[Job] = []
        failures: List[Dict[str, Any]] = []

        for raw in raw_jobs:
            try:
                jobs.append(self.map_record(raw))
            except ValidationError as exc:
                failures.append(
                    {
                        "id": raw.get("id", "<no id>"),
                        "reason": exc.reason,
                        "raw_title": raw.get("title"),
                    }
                )
            except Exception as exc:  # noqa: BLE001 - defensive: never crash the batch
                failures.append(
                    {
                        "id": raw.get("id", "<no id>"),
                        "reason": f"unexpected parse error: {exc}",
                        "raw_title": raw.get("title"),
                    }
                )

        return jobs, failures

    def _require(self, cleaned: Dict[str, Any], raw: Dict[str, Any]) -> None:
        """Check the common required fields; subclasses call this after cleaning."""
        missing = [f for f in REQUIRED_FIELDS if not cleaned.get(f)]
        if missing:
            raise ValidationError(f"missing/empty required field(s): {missing}", raw)
