# Methodology

This file says how every number in the report is made. The code is the final word. Each step names the file that does it.

## 1. Sample (`src/census/sample.py`)

The sampler splits GitHub into 72 strata: 8 languages (Python, JavaScript, TypeScript, Go, Rust, Java, C++, Ruby) times 3 star bands (10 to 99, 100 to 999, 1,000 or more) times 3 last-push years (2024, 2025, 2026). Every query also says `fork:false archived:false`.

For each stratum it makes two Search API calls. The first asks for one result to learn the total count. The second asks for one page of 15 results. The page number is drawn at random with a fixed seed (20261120), from the pages the Search API can reach (it stops at 1,000 results). The sampler does not default to the first page, because Search ranks by "best match" and the first page leans toward the most visible repos.

The sampler drops duplicates and writes `data/sample.csv` and `data/queries.json`. The second file holds every query, its total count, the page used, the seed and the date.

Each stratum gets the same number of repos, whatever its size on GitHub. So the headline numbers describe this stratified sample. They are not estimates for all of GitHub. The report also shows each stratum dimension on its own.

## 2. Collect (`src/census/collect.py`, `src/census/http.py`)

For each repo the collector asks `raw.githubusercontent.com/<repo>/HEAD/<path>` for nine fixed paths:

- Instruction files: `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `GEMINI.md`, `SKILL.md`, `.cursorrules`.
- Manifests: `package.json`, `Makefile`, `pyproject.toml`.

A 404 means the file is absent. The brief asked for the file tree first, but the session proxy blocks tree calls for other repos, so fixed paths stand in (see `docs/ENVIRONMENT.md`). Fixed paths cannot list folders. So `.cursor/rules/` folders and nested `SKILL.md` files are not covered.

Politeness rules:

- One descriptive user agent that names the project.
- A minimum gap between requests (2.1 seconds for Search, 0.25 seconds for raw files).
- The fetcher reads `x-ratelimit-remaining`, `x-ratelimit-used`, `x-ratelimit-limit` and `x-ratelimit-reset`. When the budget is spent it waits for the reset.
- On a 429, or a 403 that says "rate limit" or sends `Retry-After`, it waits (the `Retry-After` value, else 60 seconds doubling up to 15 minutes) and slows to one request a second.
- Every 200 and 404 answer goes to a disk cache, one JSON file per URL, named by the SHA-256 of the URL. A repeat run asks the network for nothing it already has.

Each repo moves through the states queued, fetched, cached and done, or failed. The states go to an append-only log, so a stopped run resumes where it stopped. A failed repo is tried again on the next run.

## 3. Analyze (`src/census/analyze.py`, `src/census/drift.py`, `src/census/dataset.py`)

Analysis reads only the cache. It never prints a collected file, and it treats every file as data.

For each instruction file it records bytes, lines, words, the number of Markdown headings, and which of five sections appear. A section counts when a heading matches its keywords:

| Section | Heading keywords |
| --- | --- |
| commands | command, build, setup, install, run, script, develop, getting started, usage, workflow |
| style | style, convention, format, lint, naming, guideline |
| testing | test, qa, verif |
| architecture | architect, structure, layout, overview, design, module, component, directory, folder |
| boundaries | boundar, don't, do not, never, restrict, rule, guardrail, security, permission, safety, avoid |

A pointer file has three lines or fewer, is under 300 bytes, and names another instruction file. Raw serves a symlink as the text of its target, so a symlinked `CLAUDE.md` is a pointer too. Section shares use only non-pointer files.

Overlap is the highest Jaccard score between the sets of normalized lines of any two non-pointer files in one repo.

### Drift

The detector scans only code: fenced blocks, inline code spans and lines that start with `$ `. It splits each line on `&&`, `||`, `;` and `|`. It finds these commands:

| Command | Manifest | Missing name counts as |
| --- | --- | --- |
| `npm run X`, `npm test` | `package.json` scripts | drift |
| `pnpm run X` | `package.json` scripts | drift |
| `yarn X`, `yarn run X`, `pnpm X`, `bun run X` | `package.json` scripts | unverifiable (may run a binary or a file) |
| `make X` | `Makefile` targets | drift, or unverifiable when the Makefile has `include` or a `%` pattern rule |
| `poe X` | `[tool.poe.tasks]` in `pyproject.toml` | drift |

A command is unverifiable when its manifest is missing or unreadable, or when it runs in a subfolder or workspace (`cd x &&`, `-C`, `-w`, `--workspace`, `--filter`, `--prefix`, `-r`). Placeholders such as `npm run <script>` are skipped.

A checkable command is one that is ok or drift. "Commands that drift" divides drifted commands by checkable commands. "Files with at least one drifted command" divides by files that have a checkable command.

### Detector check (`src/census/drift_eval.py`)

The detector is scored on 30 synthetic snippets in `eval/drift_snippets.json`. They were written and labeled for this repo and committed before the detector ran on them. A separate agent then labeled the same 30 snippets blind (`eval/blind_labels.json`) and wrote 12 hard held-out snippets of its own (`eval/heldout_snippets.json`). The detector was not changed after it saw the held-out set. Precision and recall count commands, not snippets.

## 4. Intervals (`src/census/stats.py`)

Every percentage has a 95% Wilson score interval. Wilson suits proportions because it stays inside 0 to 100 and keeps a sensible width when the count is small or near 0 or 100, where the plain normal interval breaks.

## 5. Outputs

- `data/census_repos.csv` and `.jsonl`: one row per collected repo.
- `data/census_files.csv` and `.jsonl`: one row per instruction file.
- `results/summary.json`: headline numbers and breakdowns.
- `results/drift_eval.json`: detector scores.
- `docs/report/index.html`: the static report.

The dataset holds repo names and computed numbers only. Rows are sorted, fields have a fixed order, and the only date is the collection date taken from the cache. So `census analyze` on the same cache gives the same bytes (`scripts/rebuild_check.sh`).
