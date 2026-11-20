# agents-md-census implementation plan

Goal: a `census` command that samples public repos by stratum, collects their agent instruction files politely, measures them and the drift between their commands and their manifests, and releases a dataset and a short report.

Architecture: five stages that each read the output of the one before. Sample (GitHub Search) writes `data/sample.csv`. Collect (raw file fetches with a disk cache) fills `.cache/census/`. Analyze reads only the cache and writes `data/census_*.csv|jsonl` and `results/summary.json`. Report turns the results into `docs/report/index.html` and the README table.

Stack: Python 3.11+, standard library only at run time (`urllib`, `json`, `csv`, `tomllib`), pytest and ruff for development.

Assumptions (also in `DECISIONS.md`):

- The session proxy allows Search but not trees, so collection uses fixed raw paths (brief path 2).
- Search through the proxy is authenticated, so the target is 1,000+ repos.
- Equal allocation over 72 strata. Headline numbers describe the stratified sample.

## Tasks

1. Initializer. Memory files, `init.sh`, `CLAUDE.md`, `PROJECT_CONTEXT.md`, license, gitleaks pre-commit. Check: `./init.sh` exits 0.
2. Fixtures and fake server. Synthetic repos in `tests/fixtures/`, a scripted local HTTP server in `tests/conftest.py`, an autouse guard that blocks non-local sockets. Check: the guard test fails when the guard is removed.
3. Sampler. `census.sample`: strata, query strings, seeded random page, `data/queries.json` with dates. Check: `tests/test_pipeline.py::test_sampler_saves_queries_and_is_seeded`.
4. Collector. `census.http.Fetcher` (cache named by SHA-256, header pacing, Retry-After, exponential backoff, slow to 1 request a second after a secondary limit) and `census.collect` (queued, fetched, cached, done, failed). Check: `tests/test_collect.py`, including the 403 and 429 resume test and a stop at each state.
5. Analyzer and drift. `census.analyze` (size, headings, sections, pointers, overlap) and `census.drift` (code-only command extraction, manifest parsing, ok/drift/unverifiable). Write the 30 labeled snippets first and commit them. Check: `census drift-eval`.
6. Probe and collection path. `docs/ENVIRONMENT.md`.
7. Pilot collection in the background in chunks of 400 repos.
8. Wilson intervals, dataset writer, byte-for-byte rebuild. Check: `tests/test_pipeline.py::test_rebuild_from_cache_is_byte_for_byte` and `scripts/rebuild_check.sh`.
9. Report site, `METHODOLOGY.md`, `LIMITATIONS.md`, README table generator with a test that the README matches the results.
10. Workflows: `ci.yml`, manual `pilot.yml` and `full-run.yml`. Check: actionlint.
11. README, study-later kit, release check, hand-off.
