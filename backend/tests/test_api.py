"""
Covers: (4) API job listing, (5) API search, (7) empty API response,
(8) cached data surviving a failed fetch.

fetch_jobs() is monkeypatched at the app.ingestion module level so these
tests never touch the network - they exercise the real ingestion + database
+ API code path, just with a fake source response.
"""


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["jobs_in_db"] == 0


def test_list_jobs_on_empty_database(client):
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["jobs"] == []
    assert body["total"] == 0


def test_ingest_success_populates_jobs(client, remotive_sample, monkeypatch):
    from app import ingestion as ingestion_module

    monkeypatch.setattr(ingestion_module, "fetch_jobs", lambda limit=50: remotive_sample)

    resp = client.post("/api/ingest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["fetched_count"] == 3
    assert body["inserted_count"] == 2   # 2 valid records
    assert body["failed_count"] == 1     # 1 invalid record rejected

    listing = client.get("/api/jobs").json()
    assert listing["total"] == 2


def test_search_filters_results(client, remotive_sample, monkeypatch):
    from app import ingestion as ingestion_module

    monkeypatch.setattr(ingestion_module, "fetch_jobs", lambda limit=50: remotive_sample)
    client.post("/api/ingest")

    resp = client.get("/api/jobs", params={"search": "Frontend"})
    body = resp.json()
    assert body["total"] == 1
    assert "Frontend" in body["jobs"][0]["title"]


def test_get_single_job_not_found(client):
    resp = client.get("/api/jobs/Remotive/does-not-exist")
    assert resp.status_code == 404


def test_get_single_job_found(client, remotive_sample, monkeypatch):
    from app import ingestion as ingestion_module

    monkeypatch.setattr(ingestion_module, "fetch_jobs", lambda limit=50: remotive_sample)
    client.post("/api/ingest")

    resp = client.get("/api/jobs/Remotive/1001")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Backend Engineer (Python)"


def test_empty_source_response_keeps_existing_data(client, remotive_sample, monkeypatch):
    from app import ingestion as ingestion_module

    # first ingest succeeds normally
    monkeypatch.setattr(ingestion_module, "fetch_jobs", lambda limit=50: remotive_sample)
    client.post("/api/ingest")
    assert client.get("/api/jobs").json()["total"] == 2

    # source now returns an empty job list - existing data must survive
    monkeypatch.setattr(ingestion_module, "fetch_jobs", lambda limit=50: {"jobs": []})
    resp = client.post("/api/ingest")
    assert resp.json()["status"] == "empty_source"
    assert client.get("/api/jobs").json()["total"] == 2  # unchanged


def test_fetch_failure_keeps_existing_data(client, remotive_sample, monkeypatch):
    """The 'last-known-good' fallback: a failed fetch must not wipe the DB."""
    from app import ingestion as ingestion_module

    monkeypatch.setattr(ingestion_module, "fetch_jobs", lambda limit=50: remotive_sample)
    client.post("/api/ingest")
    assert client.get("/api/jobs").json()["total"] == 2

    # simulate exhausted retries -> fetch_jobs() returns None
    monkeypatch.setattr(ingestion_module, "fetch_jobs", lambda limit=50: None)
    resp = client.post("/api/ingest")
    assert resp.json()["status"] == "fetch_failed"
    assert client.get("/api/jobs").json()["total"] == 2  # unchanged
