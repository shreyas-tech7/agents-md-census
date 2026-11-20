# Walkthrough

A tour of every file, in plain words. One idea per sentence.

## The big picture

The census has four steps. Sample picks repos. Collect downloads a few files from each one. Analyze turns the files into numbers. Report turns the numbers into a web page and a README table.

Each step reads what the step before wrote. So you can rerun any step alone.

## Code in `src/census/`

- `__init__.py` holds the version and the user agent string. GitHub asks every tool to name itself, and this string does that.
- `cli.py` is the `census` command. Each subcommand calls one function. It holds no logic of its own.
- `http.py` is the only place that touches the network. `Fetcher.get` checks the cache first. On a miss it calls `fetch`. `fetch` waits between requests, reads GitHub's rate-limit headers, and retries on 403 and 429 with longer and longer waits. `store` writes 200 and 404 answers to the cache. The cache file name is a hash of the URL, so no repo name shows up on disk. `real_token` ignores the placeholder text `proxy-injected`.
- `sample.py` builds the 72 strata. `stratum_query` writes one Search query per stratum. `sample` asks for the total count, then picks a random page with a fixed seed. `write_sample` saves the repos and every query with its date.
- `collect.py` walks the sample. Each repo moves through queued, fetched, cached and done. `StateLog` appends each move to a file, so a crash loses at most the repo in flight. `_fetch_all` asks for the six instruction files first. It asks for the three manifests only when an instruction file exists.
- `analyze.py` measures one file. `file_stats` counts bytes, lines, words and headings, and checks headings for five kinds of section. `is_pointer` spots tiny files that only point elsewhere. `max_overlap` compares the files inside one repo line by line.
- `drift.py` finds commands and checks them. `code_segments` keeps only code, so prose is skipped. `extract_commands` splits lines on `&&`, `||`, `;` and `|` and reads npm, pnpm, yarn, bun, make and poe commands. `parse_manifests` reads the scripts, targets and tasks. `check` says ok, drift or unverifiable. `self_check` runs all of it on this repo.
- `drift_eval.py` scores the detector. It counts true positives, false positives and false negatives over commands, on three inputs in `eval/`.
- `stats.py` holds the Wilson interval. `proportion` bundles a count, its interval, the method and the date.
- `dataset.py` builds the released files from the cache alone. It sorts every row and fixes the column order, so the same cache gives the same bytes. `summarize` makes the headline numbers.
- `report.py` writes `docs/report/index.html` and the README table from the results files, so no number in them is typed by hand.

## Tests in `tests/`

- `conftest.py` blocks every network call to a host that is not local. It also runs a small fake HTTP server that answers with scripted replies, and a fake clock so backoff tests run instantly.
- `test_http.py` covers the cache, the 403 and 429 retries, the reset wait and the token rule.
- `test_collect.py` stops the collector at each state and checks that a rerun finishes without refetching done repos. One test feeds it 429, then 403, then 429.
- `test_drift.py` covers the command rules, checks that the shipped detector scores match the code, and runs the self-check.
- `test_pipeline.py` runs the whole pipeline on fixtures. It checks the byte-for-byte rebuild, that no file text leaks into the dataset, the report page and that the README table matches the results.
- `fixtures/` holds made-up repos and a made-up Search answer.

## Data and results

- `data/sample.csv` lists the sampled repos with their stratum.
- `data/queries.json` lists every Search query, its count, page, seed and date.
- `data/census_repos.*` has one row per collected repo. `data/census_files.*` has one row per instruction file. Both come as CSV and JSON Lines.
- `results/summary.json` holds the headline numbers with intervals. `results/drift_eval.json` holds the detector scores.
- `eval/drift_snippets.json` holds the 30 labeled snippets. `eval/blind_labels.json` holds a second, blind set of labels. `eval/heldout_snippets.json` holds 12 harder snippets from a separate agent.

## Scripts

- `scripts/build_readme.py` writes the README results table.
- `scripts/rebuild_check.sh` rebuilds the dataset twice and compares hashes.
- `scripts/check_links.py` checks every relative link and anchor.
- `scripts/social_preview.py` draws the 1280 by 640 preview picture with no image library.

## Repo files

- `init.sh` sets up and tests everything in one command. CI runs it too.
- `Makefile` gives short names for the common commands.
- `AGENTS.md` and `CLAUDE.md` are this repo's own agent files. Every command in them exists.
- `.github/workflows/ci.yml` runs on every push. `pilot.yml` and `full-run.yml` run only by hand and commit a new dataset.
- `METHODOLOGY.md` and `LIMITATIONS.md` explain the numbers and their limits.
- `DECISIONS.md`, `BLOCKERS.md`, `PROGRESS.md` and `feature_list.json` are the build agent's memory.
- `docs/HUMAN_STEPS.md` lists what only Shreyas can do.
