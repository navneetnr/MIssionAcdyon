"""
The one internal Job shape every source adapter must produce.
Nothing downstream (DB, API, frontend) should ever see raw source fields -
only this shape. That's the whole point of normalization.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Job:
    id: str
    title: str
    company: str
    url: str
    source: str
    location: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    job_type: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    company_logo: Optional[str] = None
