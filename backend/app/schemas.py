"""Pydantic models for API request/response shapes. Kept separate from the
internal models.Job dataclass on purpose: the DB row shape and the public
API shape are allowed to drift independently (e.g. we may want to add an
API-only computed field later without touching the ingestion pipeline)."""

from typing import List, Optional

from pydantic import BaseModel


class JobOut(BaseModel):
    source: str
    external_id: str
    title: str
    company: str
    url: str
    location: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    job_type: Optional[str] = None
    salary: Optional[str] = None
    description: Optional[str] = None
    posted_date: Optional[str] = None
    company_logo: Optional[str] = None
    first_seen_at: str
    last_seen_at: str


class JobsResponse(BaseModel):
    jobs: List[JobOut]
    total: int
    limit: int
    offset: int


class IngestResponse(BaseModel):
    status: str  # "success" | "empty_source" | "fetch_failed"
    source: str
    fetched_count: int
    inserted_count: int
    updated_count: int
    failed_count: int
    total_jobs_in_db: int
    message: str


class HealthResponse(BaseModel):
    status: str
    jobs_in_db: int
