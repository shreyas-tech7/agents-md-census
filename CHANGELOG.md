# Changelog

## v0.1.0-rc1 (2026-11-20)

First release candidate.

- `census sample`: stratified Search sampler, 72 strata, seeded random page, saved queries.
- `census collect`: resumable collector over fixed raw paths, disk cache, header pacing, backoff on 403 and 429.
- `census analyze`: file statistics, sections, pointer files, overlap and command drift.
- `census report`: static report site and generated README tables with 95% Wilson intervals.
- `census drift-eval`: detector scores on 30 labeled snippets and 12 held-out snippets.
- `census self-check`: drift check on this repo's own AGENTS.md and CLAUDE.md.
- Session dataset in `data/`, manual `pilot` and `full-run` workflows.

Release commit: `bc546808a5df57dbf699c5ba4e504da9e7cb2649` on branch `claude/build-agents-md-census`. The tag waits for step 4 in `docs/HUMAN_STEPS.md`.
