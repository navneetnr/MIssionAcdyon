"""
SQLite persistence layer.

Deliberately plain stdlib sqlite3 - no ORM. The schema is small (one jobs
table, one ingestion_runs log table) and every query here is one that a
reviewer can read top to bottom, which matters more than abstraction for
a project this size.

Dedup strategy: primary key is (source, external_id). Re-ingesting the same
Remotive job just updates last_seen_at and any changed fields - it never
creates a second row. This is what makes repeated ingestion idempotent.

"Last-known-good" fallback: this module never deletes jobs as part of an
ingestion run. If a fetch fails or comes back empty, ingestion.py simply
doesn't call upsert_jobs(), so whatever is already in SQLite stays queryable.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DB_PATH = os.environ.get("DATABASE_PATH", "jobs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    source        TEXT NOT NULL,
    external_id   TEXT NOT NULL,
    title         TEXT NOT NULL,
    company       TEXT NOT NULL,
    url           TEXT NOT NULL,
    location      TEXT,
    category      TEXT,
    tags          TEXT,        -- JSON-encoded list of strings
    job_type      TEXT,
    salary        TEXT,
    description   TEXT,
    posted_date   TEXT,
    company_logo  TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    PRIMARY KEY (source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_title    ON jobs(title);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    source           TEXT NOT NULL,
    status           TEXT NOT NULL,   -- 'success' | 'empty_source' | 'fetch_failed'
    fetched_count    INTEGER DEFAULT 0,
    inserted_count   INTEGER DEFAULT 0,
    updated_count    INTEGER DEFAULT 0,
    failed_count     INTEGER DEFAULT 0,
    error_message    TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def connect(db_path: str = DEFAULT_DB_PATH):
    """Convenience context manager used by the API layer and tests."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def upsert_jobs(conn: sqlite3.Connection, jobs: List[Any]) -> Tuple[int, int]:
    """
    Insert new jobs, update existing ones (matched on source + external_id).
    Returns (inserted_count, updated_count).

    `jobs` is a list of the internal Job dataclass (models.Job) - this module
    doesn't import that type directly to avoid a circular import with the
    root-level models.py; it just reads attributes off each object.
    """
    now = _now()
    inserted = 0
    updated = 0

    for job in jobs:
        cur = conn.execute(
            "SELECT 1 FROM jobs WHERE source = ? AND external_id = ?",
            (job.source, job.id),
        )
        exists = cur.fetchone() is not None

        conn.execute(
            """
            INSERT INTO jobs (
                source, external_id, title, company, url, location, category,
                tags, job_type, salary, description, posted_date, company_logo,
                first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_id) DO UPDATE SET
                title=excluded.title,
                company=excluded.company,
                url=excluded.url,
                location=excluded.location,
                category=excluded.category,
                tags=excluded.tags,
                job_type=excluded.job_type,
                salary=excluded.salary,
                description=excluded.description,
                posted_date=excluded.posted_date,
                company_logo=excluded.company_logo,
                last_seen_at=excluded.last_seen_at
            """,
            (
                job.source,
                job.id,
                job.title,
                job.company,
                job.url,
                job.location,
                job.category,
                json.dumps(job.tags or []),
                job.job_type,
                job.salary,
                job.description,
                job.posted_date,
                job.company_logo,
                now,
                now,
            ),
        )

        if exists:
            updated += 1
        else:
            inserted += 1

    conn.commit()
    return inserted, updated


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
    return d


def get_jobs(
    conn: sqlite3.Connection,
    search: Optional[str] = None,
    category: Optional[str] = None,
    job_type: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """Returns (jobs_page, total_matching_count)."""
    where = []
    params: List[Any] = []

    if search:
        where.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if category:
        where.append("category = ?")
        params.append(category)
    if job_type:
        where.append("job_type = ?")
        params.append(job_type)
    if location:
        where.append("location LIKE ?")
        params.append(f"%{location}%")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    total = conn.execute(
        f"SELECT COUNT(*) FROM jobs {where_sql}", params
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        SELECT * FROM jobs {where_sql}
        ORDER BY posted_date DESC, last_seen_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()

    return [_row_to_dict(r) for r in rows], total


def get_job(conn: sqlite3.Connection, source: str, external_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM jobs WHERE source = ? AND external_id = ?",
        (source, external_id),
    ).fetchone()
    return _row_to_dict(row) if row else None


def count_jobs(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]


def log_ingestion_run(
    conn: sqlite3.Connection,
    source: str,
    status: str,
    fetched_count: int = 0,
    inserted_count: int = 0,
    updated_count: int = 0,
    failed_count: int = 0,
    error_message: Optional[str] = None,
    started_at: Optional[str] = None,
) -> int:
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO ingestion_runs (
            started_at, finished_at, source, status,
            fetched_count, inserted_count, updated_count, failed_count, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            started_at or now,
            now,
            source,
            status,
            fetched_count,
            inserted_count,
            updated_count,
            failed_count,
            error_message,
        ),
    )
    conn.commit()
    return cur.lastrowid
