"""
Ingestion service - ties the existing fetch/parse layer to SQLite.

    Remotive API -> fetch_jobs() -> RemotiveParser.parse_many()
        -> upsert_jobs() -> ingestion_runs log

Design choices worth calling out (see DECISIONS.md for the full version):

- If the fetch fails (network error, non-2xx, retries exhausted), we do NOT
  touch the jobs table. Whatever was ingested last time stays queryable.
  We just log a 'fetch_failed' run and return.
- If the fetch succeeds but returns zero jobs, we treat that the same way -
  an empty response is far more likely to be a source-side glitch than
  "there are truly zero remote jobs in the world right now". We log
  'empty_source' and leave existing data alone.
- Records that fail validation (missing title/company/url) are counted and
  logged, not silently dropped and not allowed to crash the run.
"""

import logging
from typing import Any, Dict

from . import _pathfix  # noqa: F401  (must run before the imports below)
from .database import get_connection, log_ingestion_run, upsert_jobs, count_jobs

from fetch_jobs import fetch_jobs  # root-level, unmodified
from parsers.remotive import RemotiveParser  # root-level, unmodified

logger = logging.getLogger("acdyon.ingestion")

SOURCE_NAME = "Remotive"


def run_ingestion(db_path: str, limit: int = 50) -> Dict[str, Any]:
    """Runs one ingestion pass. Returns a summary dict matching IngestResponse."""
    conn = get_connection(db_path)
    try:
        logger.info("Ingestion started (source=%s, limit=%s)", SOURCE_NAME, limit)
        data = fetch_jobs(limit=limit)

        if data is None:
            # Source unreachable after retries/backoff - last-known-good fallback.
            log_ingestion_run(conn, source=SOURCE_NAME, status="fetch_failed",
                               error_message="source unreachable after retries")
            existing = count_jobs(conn)
            logger.warning("Ingestion: fetch failed, keeping %s existing job(s)", existing)
            return {
                "status": "fetch_failed",
                "source": SOURCE_NAME,
                "fetched_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
                "failed_count": 0,
                "total_jobs_in_db": existing,
                "message": (
                    "Remotive API unreachable after retries. Existing data was "
                    "left untouched (last-known-good fallback)."
                ),
            }

        raw_jobs = data.get("jobs", [])

        if not raw_jobs:
            log_ingestion_run(conn, source=SOURCE_NAME, status="empty_source",
                               fetched_count=0)
            existing = count_jobs(conn)
            logger.warning("Ingestion: source returned 0 jobs, keeping %s existing job(s)", existing)
            return {
                "status": "empty_source",
                "source": SOURCE_NAME,
                "fetched_count": 0,
                "inserted_count": 0,
                "updated_count": 0,
                "failed_count": 0,
                "total_jobs_in_db": existing,
                "message": "Source returned an empty job list. Existing data was left untouched.",
            }

        parser = RemotiveParser()
        jobs, failures = parser.parse_many(raw_jobs)

        inserted, updated = upsert_jobs(conn, jobs) if jobs else (0, 0)

        log_ingestion_run(
            conn,
            source=SOURCE_NAME,
            status="success",
            fetched_count=len(raw_jobs),
            inserted_count=inserted,
            updated_count=updated,
            failed_count=len(failures),
        )

        total = count_jobs(conn)
        logger.info(
            "Ingestion complete: fetched=%s inserted=%s updated=%s failed=%s total_in_db=%s",
            len(raw_jobs), inserted, updated, len(failures), total,
        )

        return {
            "status": "success",
            "source": SOURCE_NAME,
            "fetched_count": len(raw_jobs),
            "inserted_count": inserted,
            "updated_count": updated,
            "failed_count": len(failures),
            "total_jobs_in_db": total,
            "message": f"Ingested {len(raw_jobs)} record(s): {inserted} new, {updated} updated, {len(failures)} rejected.",
        }
    finally:
        conn.close()
