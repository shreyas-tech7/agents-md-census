# Progress

Branch: `claude/build-agents-md-census`. Remote for this build: a local bare repo that stands in for GitHub (see `BLOCKERS.md`).

## Done

- Initializer: memory files, `init.sh`, `PROJECT_CONTEXT.md`, `CLAUDE.md`, plan, license, secret scan hook.
- Offline test guard, synthetic fixtures and a scripted fake server.
- Stratified sampler: 8 languages, 3 star bands, 3 push years, 15 repos per stratum, seed 20261120. Sample of 1,065 repos in `data/sample.csv`.
- Collector state machine with a hashed disk cache, header pacing, backoff and resume. All 1,065 repos collected on 2026-11-20, none failed.
- Analyzer and drift detector, scored on 30 labeled snippets and 12 held-out snippets.
- Dataset, `results/summary.json`, report site, README table and social preview, rebuilt from the full cache. The rebuild is byte for byte the same.
- CI, pilot and full-run workflows, all clean under actionlint.
- README, METHODOLOGY, LIMITATIONS, WALKTHROUGH, INTERVIEW_QA, DEMO, CHANGELOG, CONTRIBUTING, issue templates, topics, human steps and the Cowork hand-off prompt.
- All 18 features in `feature_list.json` pass their steps. An outside check from a fresh clone passed every Done-means item.

## Next

- Shreyas's steps in `docs/HUMAN_STEPS.md`, starting with creating the GitHub repo and pushing the bundle.

## Open blockers

- No GitHub repo and no working GitHub token. Push to GitHub, PR, Actions, tags and releases wait for Shreyas.

## Last `./init.sh`

Passed: lint clean, 40 tests passed offline, self-check found 0 drifted commands.
