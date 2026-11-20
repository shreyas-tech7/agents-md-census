# Decisions

One line per choice: what was picked, what else was weighed, and why.

- 2026-11-20 Name: `agents-md-census`. PyPI and npm both answer 404 for it (checked 2026-11-20) and it matches the repo name. The brief says no package is needed, so no backup names were checked.
- 2026-11-20 Collection path 2 (search works, trees answer 403): sample through Search, collect through `raw.githubusercontent.com/<repo>/HEAD/<path>` at fixed paths. Probe results are in `docs/ENVIRONMENT.md`.
- 2026-11-20 Sample size target 1,000+: the proxy adds a token to Search calls (limit 30 a minute, the authenticated search limit), so the "token" branch of Done means 4 applies. Our code never sees or sends that token.
- 2026-11-20 Strata: 8 languages x 3 star bands (10..99, 100..999, >=1000) x 3 push years (2024, 2025, 2026) = 72 strata, 15 repos each. Weighed: equal allocation vs proportional. Picked equal so every stratum has enough repos to compare. Headline numbers are therefore for the stratified sample, not the GitHub population.
- 2026-11-20 Inside a stratum the sampler picks one seeded random results page (seed 20261120). Weighed: first page, sort by updated, random page. The first page leans toward the best-match ranking, and sort by updated leans toward the end of the year.
- 2026-11-20 Added `.cursorrules` (the older single-file Cursor format) as its own format. `.cursor/rules/` folders and nested `SKILL.md` files are not covered in the pilot, because fixed paths cannot list a folder.
- 2026-11-20 Cache: one JSON file per URL, named by the SHA-256 of the URL. 200 and 404 answers are cached, so absent files are not asked for twice. The cache is git-ignored because it holds file text.
- 2026-11-20 Drift counts only strict commands: `npm run X`, `npm test`, `pnpm run X`, `make X` and `poe X`. `yarn X`, `pnpm X` and `bun run X` can fall back to a binary or a file, so a missing script there is "unverifiable", not drift.
- 2026-11-20 A command run in a subfolder or workspace (`cd x &&`, `-C`, `--workspace`, `--filter`, `--prefix`) is unverifiable, because only the root manifests are collected.
- 2026-11-20 A Makefile with `include` or a pattern rule (`%`) makes a missing target unverifiable. This costs recall (snippet S29 and held-out H10 are misses) but avoids false alarms.
- 2026-11-20 Only code is scanned for commands: fenced blocks, inline code spans and `$ ` prompt lines. Prose like "use yarn instead of npm" is skipped.
- 2026-11-20 Python coverage is `[tool.poe.tasks]` only. `uv run X`, `pdm run X` and `hatch run X` can run any installed tool, so they cannot be checked from the manifest alone.
- 2026-11-20 Pointer files: a file of three lines or fewer and under 300 bytes that names another instruction file counts as a pointer. Raw serves a symlink as its target path, so a symlinked CLAUDE.md shows up as the text "AGENTS.md".
- 2026-11-20 Overlap: highest line-set Jaccard between any two non-pointer files in a repo. Weighed: word shingles. Lines are simpler and match how people copy sections.
- 2026-11-20 Drift snippets: 30 written and labeled before the detector ran (commit 797ed84). A separate agent then labeled them blind and wrote 12 held-out snippets. The detector was not changed after it saw the held-out set.
- 2026-11-20 S26 (`bun run seed`, no seed script): first label "not drift", blind label "drift". Kept the first label, because bun runs a file named seed.ts when no script exists. Both labels are in `eval/`.
- 2026-11-20 Wilson intervals treat every unit as independent. For "commands that drift" the commands cluster inside files, so that interval is too narrow. `LIMITATIONS.md` says so.
- 2026-11-20 Social preview: a stdlib PNG writer with a small built-in pixel font, because the brief names no image library.
- 2026-11-20 Tests use synthetic fixtures in the recorded response shape, not real API answers, so no real owner logins sit in the test folder.
