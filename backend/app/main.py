"""
FastAPI app.

Endpoints:
    GET  /health
    GET  /api/jobs          (search, category, job_type, location, limit, offset)
    GET  /api/jobs/{source}/{id}
    POST /api/ingest

Run locally from the `backend/` directory:
    uvicorn app.main:app --reload --port 8000

See README.md for full setup instructions and .env.example for configuration.
"""

import logging
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from . import _pathfix  # noqa: F401  (must run before ingestion/database imports)
from .database import connect, get_jobs, get_job, count_jobs, init_db, DEFAULT_DB_PATH
from .ingestion import run_ingestion
from .schemas import HealthResponse, IngestResponse, JobsResponse

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("acdyon.api")

DB_PATH = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)

# Comma-separated list, e.g. "http://localhost:5173,https://myapp.vercel.app"
_origins_env = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_ingestion(DB_PATH, limit=50)
    yield

app = FastAPI(
    lifespan=lifespan,
    title="ACDYON Job Aggregator API",
    description="Ingests, normalizes, and serves job listings from the public Remotive API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db(DB_PATH)
    logger.info("Database ready at %s", DB_PATH)


@app.get("/health", response_model=HealthResponse)
def health():
    with connect(DB_PATH) as conn:
        return HealthResponse(status="ok", jobs_in_db=count_jobs(conn))


@app.get("/api/jobs", response_model=JobsResponse)
def list_jobs(
    search: str | None = Query(default=None, description="Matches title, company, description"),
    category: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    location: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    with connect(DB_PATH) as conn:
        jobs, total = get_jobs(
            conn,
            search=search,
            category=category,
            job_type=job_type,
            location=location,
            limit=limit,
            offset=offset,
        )
    return JobsResponse(jobs=jobs, total=total, limit=limit, offset=offset)


@app.get("/api/jobs/{source}/{external_id}")
def get_single_job(source: str, external_id: str):
    with connect(DB_PATH) as conn:
        job = get_job(conn, source, external_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/ingest", response_model=IngestResponse)
def trigger_ingestion(limit: int = Query(default=50, ge=1, le=200)):
    result = run_ingestion(DB_PATH, limit=limit)
    return IngestResponse(**result)
