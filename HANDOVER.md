# Handover

Read this if a session stops before the final report. Then read `PROGRESS.md`.

## Done

The build is complete. Every Done-means item passes. See `PROGRESS.md`.

## Next, in order

Only Shreyas's steps are left. They are in `docs/HUMAN_STEPS.md`. To refresh the dataset later:

```bash
source .venv/bin/activate
census collect --limit 200          # repeat until the output shows "queued": 0 and "failed": 0
census drift-eval && census analyze && census report
python3 scripts/build_readme.py && python3 scripts/social_preview.py
scripts/rebuild_check.sh            # the rebuild must match byte for byte
./init.sh                           # lint and all tests offline
```

## Open decisions

- None that block the build. Shreyas decides whether `docs/build/BUILD_PROMPT.md` stays public (step 9 in `docs/HUMAN_STEPS.md`).

## Resume launcher

"Read docs/build/BUILD_PROMPT.md and follow it. Resume from PROGRESS.md on branch claude/build-agents-md-census. Do not ask questions. Do not stop until every Done-means item is true or blocked with a fallback."
