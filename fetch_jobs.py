"""
Step 1-3 of the ingestion pipeline: fetch + inspect raw data from a public
job source (Remotive public API) before we build the parser/normalizer.

Source: https://remotive.com/api/remote-jobs
Docs:   https://github.com/remotive-com/remote-jobs-api

Remotive's own terms (see docs above) ask that:
  - we identify ourselves (no spoofed headers)
  - we don't hammer the endpoint (cache, don't poll aggressively)
  - we attribute Remotive + link back to the original job URL
This script is written to respect all three - which is exactly the
"honest client" behavior the assignment's Detection Surface section
(headers / timing / behavioral patterns) is asking us to demonstrate.

Run locally with:  python fetch_jobs.py
Requires:           pip install requests
"""

import time
import json
import sys
import requests

BASE_URL = "https://remotive.com/api/remote-jobs"

# Honest, identifying headers - we say who we are instead of
# spoofing a browser's User-Agent.
HEADERS = {
    "User-Agent": "ACDYON-JobAggregator/0.1 (student project; contact: you@example.com)",
    "Accept": "application/json",
}

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT = 10


def fetch_jobs(limit: int = 20, category: str | None = None):
    """
    Fetch jobs from Remotive with retry + exponential backoff.
    Returns the parsed JSON dict on success, or None if all retries failed.
    """
    params = {"limit": limit}
    if category:
        params["category"] = category

    attempt = 0
    while attempt <= MAX_RETRIES:
        try:
            response = requests.get(
                BASE_URL, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT
            )
        except requests.exceptions.RequestException as exc:
            print(f"[attempt {attempt + 1}] network error: {exc}")
            response = None

        if response is not None:
            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                print(f"[attempt {attempt + 1}] rate limited (429).")
            elif response.status_code >= 500:
                print(f"[attempt {attempt + 1}] server error ({response.status_code}).")
            else:
                # 4xx other than 429 usually means our request is wrong,
                # not a transient failure - don't waste retries on it.
                print(f"Non-retryable status: {response.status_code}")
                print(response.text[:500])
                return None

        attempt += 1
        if attempt <= MAX_RETRIES:
            wait = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            print(f"  retrying in {wait}s...")
            time.sleep(wait)

    print("Max retries exceeded. Source unavailable - fall back to cached data.")
    return None


def inspect_structure(data: dict):
    """Step 3: print the raw response shape so we can design the parser."""
    print("\nTop-level keys:", list(data.keys()))

    jobs = data.get("jobs", [])
    total = data.get("total-job-count", len(jobs))
    print(f"Jobs returned this call: {len(jobs)}  |  Source reports total: {total}")

    if not jobs:
        # This is the "empty response" resilience case from Section 8 -
        # flag it rather than silently treating it as "zero jobs exist".
        print("WARNING: empty job list. Do not overwrite cached data with this.")
        return

    print("\nSample job record (raw, first item):")
    print(json.dumps(jobs[0], indent=2)[:1000])

    print("\nFields present on first job:", list(jobs[0].keys()))


if __name__ == "__main__":
    data = fetch_jobs(limit=10)
    if data is None:
        sys.exit(1)
    inspect_structure(data)
