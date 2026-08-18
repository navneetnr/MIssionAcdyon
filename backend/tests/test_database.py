"""
Covers: (3) database deduplication, (6) empty database.
"""

from app.database import (
    get_connection,
    init_db,
    upsert_jobs,
    get_jobs,
    get_job,
    count_jobs,
)
from models import Job


def _make_job(job_id="1001", title="Backend Engineer", company="Acme", **overrides):
    defaults = dict(
        id=job_id,
        title=title,
        company=company,
        url=f"https://remotive.com/remote-jobs/{job_id}",
        source="Remotive",
        category="Software Development",
        location="Worldwide",
        job_type="full_time",
        tags=["python"],
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_empty_database_returns_no_jobs(db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    jobs, total = get_jobs(conn)
    assert jobs == []
    assert total == 0
    assert count_jobs(conn) == 0
    conn.close()


def test_upsert_inserts_new_job(db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    inserted, updated = upsert_jobs(conn, [_make_job()])
    assert inserted == 1
    assert updated == 0
    assert count_jobs(conn) == 1
    conn.close()


def test_upsert_same_source_and_id_deduplicates(db_path):
    """Re-ingesting the same (source, external_id) must update, not duplicate."""
    init_db(db_path)
    conn = get_connection(db_path)

    upsert_jobs(conn, [_make_job(title="Backend Engineer v1")])
    inserted, updated = upsert_jobs(conn, [_make_job(title="Backend Engineer v2")])

    assert inserted == 0
    assert updated == 1
    assert count_jobs(conn) == 1  # still exactly one row

    job = get_job(conn, "Remotive", "1001")
    assert job["title"] == "Backend Engineer v2"  # field was updated
    conn.close()


def test_get_jobs_filters_by_category_and_search(db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    upsert_jobs(conn, [
        _make_job(job_id="1", title="Backend Engineer", category="Engineering"),
        _make_job(job_id="2", title="Sales Manager", category="Sales"),
    ])

    eng_only, total_eng = get_jobs(conn, category="Engineering")
    assert total_eng == 1
    assert eng_only[0]["title"] == "Backend Engineer"

    search_result, total_search = get_jobs(conn, search="Sales")
    assert total_search == 1
    assert search_result[0]["title"] == "Sales Manager"
    conn.close()
