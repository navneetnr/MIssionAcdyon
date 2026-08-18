# Remote Departures — ACDYON Frontend Challenge (Part 1)

A small full-stack job board that ingests real listings from the public
[Remotive API](https://remotive.com/api-doc), normalizes them into a common
shape, stores them in SQLite with deduplication, and serves them through a
FastAPI backend to a React/Vite frontend.

Submitted for ACDYON Technologies' **"Frontend Challenge – Build It Like You
Mean It" — Part 1: Getting Data Out of a Platform That Doesn't Want You To.**

See [`DECISIONS.md`](./DECISIONS.md) for the reasoning behind the approach,
the trade-off made under the time limit, and an honest account of where AI
was used and what was verified afterward. Read that alongside this file —
it explains *why*, this file explains *how to run it*.

---

## 1. Assignment context

The brief asks for a live demo pulling job listings from a real source,
using either a public job-board API or a sandbox — explicitly **not** a live
LinkedIn account, and not scraping evasion techniques generally. This
project uses Remotive's public JSON API as that source. Full reasoning for
that choice is in DECISIONS.md §1.

## 2. Architecture

```
Remotive public API  (https://remotive.com/api/remote-jobs)
        │  GET, honest User-Agent, retry + exponential backoff
        ▼
fetch_jobs.py          — fetches raw JSON, never crashes on failure
        ▼
parsers/remotive.py    — maps Remotive's field names onto the common Job shape
        ▼
models.py (Job)        — the one shape everything downstream depends on
        ▼
parsers/base.py        — validation (title/company/url required),
                          collects failures without crashing the batch
        ▼
backend/app/database.py — SQLite upsert, dedup on (source, external_id)
        ▼
backend/app/main.py     — FastAPI: GET /health, GET /api/jobs,
                           GET /api/jobs/{source}/{id}, POST /api/ingest
        ▼
frontend/ (React + Vite) — search, filters, job cards, loading/empty/error states
```

Design principle: nothing below `models.py` in this diagram ever sees a raw
Remotive field name. Adding a second source later means writing one new
`SourceParser` subclass — the database, API, and frontend don't change.

## 3. Folder structure

```
.
├── fetch_jobs.py            # Remotive fetcher (retry/backoff, honest headers)
├── models.py                 # Job dataclass — the common internal shape
├── parsers/
│   ├── base.py                # SourceParser ABC + shared validation loop
│   └── remotive.py            # Remotive → Job field mapping
├── demo_parse.py             # standalone fetch→parse smoke test (no server needed)
├── requirements.txt           # deps for the two files above only
│
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app + endpoints
│   │   ├── database.py         # SQLite schema, upsert/dedup, queries
│   │   ├── ingestion.py        # orchestrates fetch → parse → validate → store
│   │   ├── schemas.py          # Pydantic response models
│   │   └── _pathfix.py         # lets backend/app import the root-level modules above
│   ├── tests/
│   │   ├── fixtures/remotive_sample.json
│   │   ├── test_parsers.py
│   │   ├── test_database.py
│   │   └── test_api.py
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js               # fetch wrapper, reads VITE_API_URL
│   │   ├── index.css
│   │   └── components/
│   │       ├── Header.jsx
│   │       ├── Controls.jsx     # search + filters
│   │       ├── JobCard.jsx
│   │       └── StatusStates.jsx # loading / empty / error
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── DECISIONS.md
├── README.md
└── .gitignore
```

## 4. Backend setup

Requires Python 3.10+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # adjust DATABASE_PATH / CORS_ORIGINS if needed

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. The SQLite file (`jobs.db` by
default) and its schema are created automatically on startup.

## 5. Frontend setup

Requires Node 18+.

```bash
cd frontend
npm install
cp .env.example .env             # set VITE_API_URL if backend isn't on localhost:8000

npm run dev
```

The app is now at `http://localhost:5173`.

## 6. Running ingestion

The database starts empty. Populate it by calling the ingest endpoint (the
backend must be running):

```bash
curl -X POST "http://localhost:8000/api/ingest?limit=50"
```

You can also run the fetch/parse steps standalone, without the server or
database, for a quick sanity check of just the ingestion core:

```bash
pip install -r requirements.txt   # just `requests`, from the repo root
python demo_parse.py
```

Re-running `/api/ingest` is safe — jobs are deduplicated on
`(source, external_id)`, so repeated calls update existing rows instead of
creating duplicates.

## 7. Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

Tests use a fixture file (`tests/fixtures/remotive_sample.json`) with mock
Remotive-shaped records and monkeypatch `fetch_jobs()` — they never call the
real network, so they run the same in CI as locally. Coverage:

| File | Covers |
|---|---|
| `test_parsers.py` | valid record → normalized `Job`; invalid record (missing title) rejected without crashing the batch; tag de-duplication |
| `test_database.py` | empty database returns `[]`/`0`; new job insert; re-ingesting the same `(source, external_id)` updates instead of duplicating; category/search filtering |
| `test_api.py` | `/health`; `/api/jobs` on an empty DB; `/api/ingest` success path; `/api/jobs?search=`; `/api/jobs/{source}/{id}` found + 404; an empty-source response leaving existing data untouched; a failed fetch leaving existing data untouched (last-known-good fallback) |

**Honesty note**: `pytest` and `npm run build` could not be executed inside
the sandbox this project was assembled in — its network is allowlisted and
does not include PyPI, npm, or remotive.com. What *was* verified there: every
`.py` file compiles, every `.jsx`/`.js` file was bundled with `esbuild`
(catches syntax and import errors) with zero warnings in ESM mode, and the
parser + SQLite dedup logic was executed directly (not via pytest) against
the same fixture, producing the exact results the tests above assert. Run
`pytest -v` and `npm run build` yourself before submitting — see
DECISIONS.md §3 for the full account.

## 8. API endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | `{ "status": "ok", "jobs_in_db": <int> }` |
| `GET` | `/api/jobs` | Query params: `search`, `category`, `job_type`, `location`, `limit` (default 20, max 100), `offset` |
| `GET` | `/api/jobs/{source}/{external_id}` | e.g. `/api/jobs/Remotive/1234567`; `404` if not found |
| `POST` | `/api/ingest?limit=50` | Runs one ingestion pass; returns counts and status (`success` / `empty_source` / `fetch_failed`) |

Interactive docs (Swagger UI) are available at `http://localhost:8000/docs`
once the backend is running.

## 9. Environment variables

**Backend** (`backend/.env`, see `backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `jobs.db` | SQLite file path |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | stdlib logging level |

**Frontend** (`frontend/.env`, see `frontend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `https://missionacdyon.onrender.com` | backend base URL used by every fetch call |

No secrets are required anywhere in this project — the Remotive API is
public and unauthenticated. Nothing sensitive is committed; `.env` files are
git-ignored.

## 10. Deployment

Simplest split that fits this architecture, and the one this project is
configured for:

- **Frontend → Vercel or Netlify.** It's a static Vite build
  (`npm run build` → `frontend/dist/`). Set `VITE_API_URL` to your deployed
  backend URL as a build-time environment variable on whichever platform you
  use.
- **Backend → Render or Railway**, using `backend/Dockerfile`, or their
  native "detect requirements.txt + run a start command" flow with:
  ```
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
  (working directory `backend/`). Set `CORS_ORIGINS` to your deployed
  frontend's URL once you have it, and redeploy.

No Kubernetes, no message queue, no separate cache layer — a two-service
deploy is all this architecture needs.

**This project's deployment has not been performed or tested** — only the
configuration for it (Dockerfile, CORS, env-driven URLs) has been prepared
and reasoned through. Don't claim a live deployed demo without actually
deploying and clicking through it first.

## 11. Limitations

- **SQLite on most free-tier PaaS hosts (Render, Railway free tiers, etc.)
  sits on an ephemeral filesystem** — a redeploy or restart can wipe
  `jobs.db`. That's fine for a take-home demo (just re-run `/api/ingest`
  after a redeploy), but it is not what you'd ship for anything real; swap
  in Postgres (or a mounted persistent volume, where the host supports one)
  before treating this as production.
- Only one source is wired up (Remotive). The adapter pattern
  (`SourceParser`) is built for more, but a second source was not
  implemented — see DECISIONS.md §2.
- `POST /api/ingest` runs synchronously in the request — there's no
  scheduler. For a demo this is fine (you trigger it manually); for
  production you'd want a cron job or background task instead.
- No auth on `/api/ingest` — anyone who can reach the backend can trigger a
  fetch. Acceptable for a public-data demo; would need protecting (API key
  or admin-only route) if this were long-lived.

## 12. AI usage disclosure

This project was built with Claude (Anthropic) as the primary author of the
backend, frontend, and test code, across two sessions — continuing an
earlier session's fetcher/parser work and building the remaining layers
against the ACDYON brief. See DECISIONS.md §3 for exactly what was
independently verified in-session (parser/database logic, executed
directly; every file's syntax) versus what still needs a real `pytest` /
`npm run build` run in an environment with normal internet access before
submission.
