# DECISIONS.md

## 1. Ingestion strategy: public API over the obvious alternative

The obvious alternative for "getting job data out of a platform" is scraping
LinkedIn (or Indeed/Naukri) directly — logging into an account, parsing
rendered HTML, rotating identities to dodge rate limits. That was rejected on
purpose, not for lack of ability to build it:

- It violates the platforms' terms of service and, depending on jurisdiction,
  computer-misuse law — this isn't a gray area worth defending in a take-home.
- It's structurally fragile: markup changes, A/B tests, and anti-bot measures
  break it constantly, so the "engineering" mostly becomes an arms race
  against detection rather than a data pipeline.
- The assignment itself explicitly asks for a public job-board API or a
  sandbox instead of a live LinkedIn account.

**Remotive's public API** (`GET https://remotive.com/api/remote-jobs`) was
used instead: no auth required, a documented and stable JSON shape, and it's
meant to be consumed programmatically. The fetcher identifies itself with a
real, non-spoofed `User-Agent` naming the project, retries only on
transient failures (429 / 5xx) with exponential backoff, and gives up
cleanly on non-retryable 4xx rather than hammering the endpoint. That's the
"honest client" behavior the brief's detection-surface section is really
asking for — not evasion, but a client that behaves like it has nothing to
hide.

## 2. Biggest trade-off under the time limit

**Single source, single-process ingestion.** The parser layer is designed so
a second source (e.g. Arbeitnow) is one new `SourceParser` subclass — the
base class, database, and API don't change. But only Remotive is actually
wired up, and ingestion runs synchronously inside a request (`POST
/api/ingest`) rather than on a schedule.

With a real week, next steps in priority order:
1. A second live source, to actually prove the adapter pattern under a real
   second schema instead of just an interface.
2. A scheduled/background ingestion job (cron or APScheduler) instead of
   ingest-on-request, so the frontend never triggers a slow fetch itself.
3. Swap SQLite for Postgres before any real deployment — SQLite's file is
   fine for a demo but doesn't survive most PaaS free-tier redeploys (see
   README "Limitations").
4. Pagination cursors instead of offset/limit, and structured (JSON) logs
   instead of stdlib `logging` text.

## 3. Where AI was used, and what was verified afterward

This entire codebase — fetcher, parser, SQLite layer, FastAPI backend, React
frontend, and this test suite — was written by Claude (Anthropic) working
directly in the repository, continuing a prior session's fetcher/parser
code and building the rest from the ACDYON brief.

What was genuinely verified in this environment, and what wasn't:

- **Verified for real:** every Python file compiles (`py_compile`); every
  React/JS file was bundled with `esbuild` (JSX transform + import
  resolution + a clean ESM build with zero warnings) to catch syntax and
  import errors. The parser and SQLite dedup logic were executed directly
  against a temp database and the mock Remotive fixture — a valid record
  parses into a `Job`, an invalid one (missing title) is rejected without
  crashing the batch, and re-ingesting the same `(source, external_id)`
  updates one row instead of creating a duplicate. All of that ran and
  passed in this session.
- **Not verified here, honestly:** this sandbox's outbound network is
  allowlisted and does not include `remotive.com`, `pypi.org`, or the npm
  registry, so `pip install fastapi/pytest`, `npm install`, `pytest`
  itself, `npm run build`, and a live call to Remotive could not be run in
  this environment. The FastAPI/pytest/React code was written and manually
  traced against the verified database/parser logic underneath it, but the
  actual `pytest` run and `npm run build` still need to happen once, in an
  environment with normal internet access, before this is submitted as
  "tested." Do not take "14 tests" or "build succeeded" as claims made in
  this session — they weren't independently re-run here after this
  rewrite.

Nothing about LinkedIn/Indeed/Naukri scraping, CAPTCHA bypass, or evasion
was implemented at any point, in this session or the one before it.

## Other decisions, briefly

- **Validation**: required fields are `title`, `company`, `url` — a record
  missing any of these is logged with a reason and excluded, never allowed
  to silently corrupt the dataset or crash the batch.
- **Deduplication**: primary key `(source, external_id)` in SQLite, with
  `INSERT ... ON CONFLICT DO UPDATE`, so re-running ingestion is idempotent.
- **Resilience**: a failed fetch (after retries) or an empty job list from
  the source never deletes or overwrites existing rows — the API keeps
  serving the last successfully ingested data, and the run is logged as
  `fetch_failed` or `empty_source` rather than silently succeeding.
- **If Remotive is later replaced by an official/partner API**: only
  `parsers/remotive.py` and the URL in `fetch_jobs.py` would change. The
  `Job` model, database, and API are already source-agnostic.
