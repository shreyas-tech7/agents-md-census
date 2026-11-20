# Progress

Branch: `claude/build-agents-md-census`. Remote for this build: a local bare repo that stands in for GitHub (see `BLOCKERS.md`).

## Done

- Initializer: memory files, `init.sh`, `PROJECT_CONTEXT.md`, `CLAUDE.md`, plan, license, secret scan hook.
- Offline test guard, synthetic fixtures and a scripted fake server.
- Stratified sampler: 8 languages, 3 star bands, 3 push years, 15 repos per stratum, seed 20261120. Sample of 1,065 repos in `data/sample.csv`.
- Collector state machine with a hashed disk cache, header pacing, backoff and resume. The 403 and 429 test passes.
- Analyzer and drift detector, scored on 30 labeled snippets and 12 held-out snippets.
- Wilson intervals, dataset writer, report site, README table generator, social preview.
- CI, pilot and full-run workflows, all clean under actionlint.
- README, METHODOLOGY, LIMITATIONS, WALKTHROUGH, CHANGELOG, CONTRIBUTING, issue templates, topics, human steps and the Cowork hand-off prompt.

## Next

- Finish collecting the remaining repos (`census collect`, run again until no repo is queued or failed).
- Rebuild the dataset and report, then refresh the README table and social preview.
- Write `docs/INTERVIEW_QA.md` and `docs/DEMO.md` from the final numbers.
- Run every feature's steps and set the `passes` flags.
- Outside check from a fresh clone, release commit, bundle and final report.

## Open blockers

- No GitHub repo and no working GitHub token. Push, PR, Actions, tags and releases wait for Shreyas. See `docs/HUMAN_STEPS.md`.

## Last `./init.sh`

Passed: lint clean, 40 tests passed offline.
