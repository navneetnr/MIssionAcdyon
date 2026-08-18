"""
The fetcher/parser layer (fetch_jobs.py, models.py, parsers/) lives at the
repo root - it was already built and tested before the backend existed, and
there's no reason to move or duplicate it just to satisfy a package layout.

This tiny module puts the repo root on sys.path so backend/app/*.py can do
plain `from models import Job` / `from parsers.remotive import RemotiveParser`
/ `from fetch_jobs import fetch_jobs`, regardless of the current working
directory the server is started from.

Imported once, first, by every backend/app module that needs the ingestion
layer.
"""

import os
import sys

_BACKEND_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_APP_DIR, "..", ".."))

if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
