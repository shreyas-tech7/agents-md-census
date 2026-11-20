# Interview questions and answers

Each answer points to the code (file and function) and to a result (file and number). The census numbers come from `results/summary.json`. The detector scores come from `results/drift_eval.json`.

### 1. What does this project do, in one breath?

It draws a stratified sample of public GitHub repos, fetches their agent instruction files (`AGENTS.md`, `CLAUDE.md` and four others) plus their root manifests, and measures two things: what the files contain and how often their commands drift from the manifests. The pipeline is `census sample`, `census collect`, `census analyze`, `census report` in `src/census/cli.py`. The census covers 1,065 repos (`results/summary.json`, `n_repos`).

### 2. Why stratified sampling and not the first page of search results?

The first page of a search sorted by stars is all famous repos, and the first page sorted by "best match" depends on GitHub's ranking, which nobody can reproduce. `sample.strata()` in `src/census/sample.py` crosses 8 languages, 3 star bands and 3 push years into 72 cells. `sample.sample()` asks each cell for its count, then picks one page at random with a seeded `random.Random(20261120)`. So small repos and old repos get the same share as popular ones, and anyone can rerun the draw from `data/queries.json`, which stores every query, its count, the page picked and the date. The cost is that cells get equal weight, so the sample over-represents popular repos compared with all of GitHub. `LIMITATIONS.md` says so.

### 3. Why only 1,000 results per query, and how does the sampler cope?

The Search API never returns more than 1,000 results for one query. `SEARCH_CAP = 1000` in `src/census/sample.py` caps the page range, so the random page always exists. Splitting by language, stars and push year keeps each query small enough that the cap cuts less of it.

### 4. How does the collector stay inside rate limits?

`Fetcher` in `src/census/http.py` reads the `x-ratelimit-*` headers on every answer. `_note_primary_limit()` waits until the reset time once the budget is spent. `_exhausted()` treats `used >= limit` as spent too, because the proxy in this session kept `remaining` fixed at 30. On a 429, or a 403 that carries `Retry-After` or says "rate limit", `_backoff()` waits for `Retry-After`, else doubles from 60 seconds up to 900, and `fetch()` then slows to one request a second for the rest of the run. The collector also asks for manifests only when a repo has an instruction file (`_fetch_all()` in `src/census/collect.py`), which kept the run at 6.9 raw requests per repo (`results/summary.json`, `cost`).

### 5. What happens if the collector stops halfway?

`collect()` in `src/census/collect.py` is a state machine: queued, fetched, cached, done, or failed. `StateLog` appends each change to `.cache/census/collect_state.jsonl`, so a crash loses at most the repo in flight. On restart, done repos are skipped, cached repos are finished from disk, and failed repos are tried again. `tests/test_collect.py::test_resume_after_stop_at_each_state` stops the run at each state and checks that the next run finishes without fetching a done repo again.

### 6. How do you prove the backoff works without hitting GitHub?

`tests/conftest.py` blocks every non-local connection for the whole test run, and `FakeServer` answers from a script. `tests/test_collect.py::test_403_and_429_back_off_then_resume` serves a 429, then a 403 with `Retry-After: 5`, then another 429. The test checks that the fake clock slept 5 seconds and the exponential wait, that the run stops cleanly when retries run out, and that the next run finishes all three repos. `tests/test_http.py::test_guard_blocks_non_local_hosts` proves the guard itself works.

### 7. Why Wilson intervals?

Many of the proportions here are small or near 0%, like `SKILL.md` at 0.0% (0 of 1065, CI 0.0 to 0.4). The simple "p plus or minus 1.96 standard errors" interval can go below 0% there, and it is too narrow for small counts. The Wilson score interval stays inside 0 to 100% and keeps close to its stated 95% coverage even when n is small. `stats.wilson()` in `src/census/stats.py` computes it, and `stats.proportion()` attaches n, method and date to every number. `tests/test_pipeline.py::test_wilson_known_values` checks it against known values.

### 8. What is drift, exactly?

A command drifts when an instruction file names a script or target that the root manifest does not define, for example `npm run typecheck` in a repo whose `package.json` has no `typecheck` script. `drift.check()` in `src/census/drift.py` gives each command one of three verdicts: ok, drift or unverifiable. In this census, 3.5% (8 of 230, CI 1.8 to 6.7) of checkable commands drift (`results/summary.json`, "Checkable commands that drift").

### 9. What does the drift check miss?

It checks root manifests only, so a command meant for a subfolder is called unverifiable, not wrong. It covers npm, pnpm, yarn and bun scripts, Make targets and poe tasks, and nothing for Cargo, Go, Gradle, just or `uv run`. It reads code only: fenced blocks, inline code and `$ ` prompt lines (`drift.code_segments()`), so a command written in prose is skipped. On the 12 held-out snippets it missed PowerShell prompts, `bash -c "..."` and a Make pattern rule, which gives recall of 72.7% there (`results/drift_eval.json`, `heldout`). `LIMITATIONS.md` lists all of this.

### 10. How do you avoid false alarms?

The detector says "unverifiable" whenever it cannot be sure. A command after `cd`, `-C`, `--workspace`, `--filter` and similar flags is scoped, so it is skipped. `yarn foo` and `bun run foo` can run a binary instead of a script, so a missing name is not drift. A `Makefile` with `include` or a `%` pattern rule may define targets the parser cannot see. When the same command shows up both scoped and at the root, `drift_report()` keeps the root verdict. Precision on the 30 labeled snippets is 100% (11 of 11) and on the 12 held-out snippets 100% (8 of 8).

### 11. How was the detector scored, and why trust the labels?

`eval/drift_snippets.json` holds 30 snippets with their manifests and the expected drift, written and committed before the detector first ran on them (commit `797ed84`). `drift_eval.score()` gives precision 100% (CI 74.1 to 100) and recall 91.7% (11 of 12, CI 64.6 to 98.5). A second, blind labeler agreed on 29 of 30 snippets (96.7%). A separate agent wrote 12 held-out snippets that the detector was never tuned on. All of it is in `results/drift_eval.json`, and `tests/test_drift.py::test_eval_matches_results_file` fails if the shipped numbers drift from the code.

### 12. How do you make a rerun give the same bytes?

`dataset.build()` in `src/census/dataset.py` reads only the cache, sorts every row, writes a fixed field order and uses no timestamp except the collection date stored in the cache. `scripts/rebuild_check.sh` runs `census analyze` twice and compares SHA-256 hashes, and `tests/test_pipeline.py::test_rebuild_from_cache_is_byte_for_byte` does the same in the test suite.

### 13. What data does the release hold, and what does it leave out?

Repo names and computed numbers only: sizes, section flags, overlap and drift counts (`REPO_FIELDS` and `FILE_FIELDS` in `src/census/dataset.py`). No file text, no authors and no emails. The raw files stay in `.cache/`, which is git-ignored and named by hash. The report shows totals only and never calls out one repo. `tests/test_pipeline.py::test_dataset_counts_and_privacy` checks that no file text leaks into the outputs.

### 14. What did the census find?

Of 1,065 repos, 8.5% (90 of 1065, CI 6.9 to 10.3) have at least one agent instruction file and 6.0% (64 of 1065, CI 4.7 to 7.6) have `AGENTS.md`. Among repos with a file, 37.8% (34 of 90, CI 28.5 to 48.1) use two or more formats, and 22.5% (29 of 129, CI 16.1 to 30.4) of files only point to another one. Of files with a checkable command, 5.6% (2 of 36, CI 1.5 to 18.1) have at least one drifted command. Every number has its Wilson interval in the README table and in `results/summary.json`, dated 2026-11-20.

### 15. What did the census cost?

No model calls and $0. The run made 144 Search requests and 7,350 raw file requests (`results/summary.json`, `cost`). Time is the real cost: at one request a second after a secondary limit, the collector did between about 6 and 37 repos a minute in the build session.

### 16. Why does this repo have its own `AGENTS.md`?

To practice what it measures. `census self-check` runs `drift.self_check()` on this repo's `AGENTS.md` and `CLAUDE.md` against its own `Makefile` and `pyproject.toml`, and CI fails if any command drifts (`.github/workflows/ci.yml`). `tests/test_drift.py::test_this_repo_has_no_drift` does the same offline.

### 17. What would you build next?

A staleness measure that compares each file's last commit with the repo's last push, and weights by stratum size to estimate GitHub-wide shares. Then the two held-out misses (PowerShell prompts and `bash -c`) and more ecosystems in the drift check (Cargo, just, Taskfile, `uv run`). `docs/PROPOSALS.md` has the list.
