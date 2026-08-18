"""
Step 4-6 demo: fetch -> parse -> normalize -> validate.

Run:  python demo_parse.py
(needs fetch_jobs.py, models.py, and parsers/ in the same folder)
"""

from fetch_jobs import fetch_jobs
from parsers.remotive import RemotiveParser


def main():
    data = fetch_jobs(limit=15)
    if data is None:
        print("Fetch failed after retries - nothing to parse.")
        print("(This is the 'fallback to cached data' branch in a real pipeline.)")
        return

    raw_jobs = data.get("jobs", [])
    print(f"Fetched {len(raw_jobs)} raw job records.\n")

    parser = RemotiveParser()
    jobs, failures = parser.parse_many(raw_jobs)

    print(f"Normalized OK: {len(jobs)}")
    print(f"Failed validation: {len(failures)}\n")

    print("--- Sample normalized jobs ---")
    for job in jobs[:3]:
        print(f"[{job.source}] {job.title} @ {job.company}")
        print(f"  location: {job.location}")
        print(f"  tags: {job.tags}")
        print(f"  posted: {job.posted_date}")
        print(f"  url: {job.url}\n")

    if failures:
        print("--- Records that failed validation ---")
        for f in failures:
            print(f"  id={f['id']} title={f['raw_title']!r} -> {f['reason']}")


if __name__ == "__main__":
    main()
