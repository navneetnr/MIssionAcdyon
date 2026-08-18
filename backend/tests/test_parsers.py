"""
Covers: (1) valid parser input, (2) invalid parser input.

Uses the existing, unmodified parsers/remotive.py against the fixture in
tests/fixtures/remotive_sample.json, which has 2 valid records and 1
deliberately invalid one (empty title).
"""

from parsers.remotive import RemotiveParser


def test_valid_records_normalize_correctly(remotive_sample):
    parser = RemotiveParser()
    jobs, failures = parser.parse_many(remotive_sample["jobs"])

    assert len(jobs) == 2
    assert len(failures) == 1

    first = next(j for j in jobs if j.id == "1001")
    assert first.title == "Backend Engineer (Python)"
    assert first.company == "Acme Remote Co"          # company_name -> company
    assert first.location == "Worldwide"                # candidate_required_location -> location
    assert first.posted_date == "2026-08-01T12:00:00"    # publication_date -> posted_date
    assert first.source == "Remotive"
    assert "python" in first.tags


def test_invalid_record_is_rejected_not_crashed(remotive_sample):
    parser = RemotiveParser()
    jobs, failures = parser.parse_many(remotive_sample["jobs"])

    assert failures[0]["id"] == 1003
    assert "missing/empty required field(s)" in failures[0]["reason"]
    # the batch as a whole must not raise, and the other 2 records still parse
    assert len(jobs) == 2


def test_tags_are_deduplicated_and_order_preserved():
    parser = RemotiveParser()
    raw = {
        "id": 42,
        "title": "Test Job",
        "company_name": "Test Co",
        "url": "https://example.com/42",
        "tags": ["python", "python", "django", "python"],
    }
    job = parser.map_record(raw)
    assert job.tags == ["python", "django"]
