"""
Remotive-specific mapping: raw Remotive JSON field -> our internal Job field.

    company_name              -> company
    candidate_required_location -> location
    publication_date           -> posted_date
    (everything else maps ~1:1 or gets dropped, e.g. company_logo_url is a
     duplicate of company_logo in Remotive's payload, so we only keep one)

This is the ONLY file that knows Remotive's field names. If Remotive changes
its response shape tomorrow, this is the only file that needs to change.
"""

from typing import Any, Dict, List

from models import Job
from parsers.base import SourceParser, ValidationError, clean_str


def _normalize_tags(raw_tags: Any) -> List[str]:
    """Remotive returns tags as a list of strings; be defensive anyway."""
    if not raw_tags:
        return []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    cleaned = []
    for t in raw_tags:
        t = clean_str(t)
        if t and t not in cleaned:  # dedupe, preserve order
            cleaned.append(t)
    return cleaned


class RemotiveParser(SourceParser):
    SOURCE_NAME = "Remotive"

    def map_record(self, raw: Dict[str, Any]) -> Job:
        cleaned = {
            "id": clean_str(raw.get("id")),
            "title": clean_str(raw.get("title")),
            "company": clean_str(raw.get("company_name")),
            "url": clean_str(raw.get("url")),
        }

        self._require(cleaned, raw)  # raises ValidationError if title/company/url missing

        if not cleaned["id"]:
            # Remotive always sends an id in practice, but don't trust it blindly.
            raise ValidationError("missing/empty required field(s): ['id']", raw)

        return Job(
            id=cleaned["id"],
            title=cleaned["title"],
            company=cleaned["company"],
            url=cleaned["url"],
            source=self.SOURCE_NAME,
            location=clean_str(raw.get("candidate_required_location")),
            category=clean_str(raw.get("category")),
            tags=_normalize_tags(raw.get("tags")),
            job_type=clean_str(raw.get("job_type")),
            salary=clean_str(raw.get("salary")),
            description=clean_str(raw.get("description")),
            posted_date=clean_str(raw.get("publication_date")),
            company_logo=clean_str(raw.get("company_logo") or raw.get("company_logo_url")),
        )
