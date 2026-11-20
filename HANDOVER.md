# Handover

Read this if a session stops before the final report. Then read `PROGRESS.md`.

## Done

Everything in `PROGRESS.md` under "Done". The code, tests, docs and workflows are complete. The only long job is collection.

## Next, in order

```bash
source .venv/bin/activate
census collect --limit 200          # repeat until the output shows "queued": 0 and "failed": 0
census drift-eval && census analyze && census report
python3 scripts/build_readme.py && python3 scripts/social_preview.py
scripts/rebuild_check.sh            # the rebuild must match byte for byte
./init.sh                           # lint and all tests offline
```

Then write `docs/INTERVIEW_QA.md` and `docs/DEMO.md` from the final numbers, set the `passes` flags in `feature_list.json`, commit with `gitleaks git --pre-commit --redact --staged`, and push.

## Open decisions

- None that block the build. Shreyas decides whether `docs/build/BUILD_PROMPT.md` stays public (step 9 in `docs/HUMAN_STEPS.md`).

## Resume launcher

"Read docs/build/BUILD_PROMPT.md and follow it. Resume from PROGRESS.md on branch claude/build-agents-md-census. Do not ask questions. Do not stop until every Done-means item is true or blocked with a fallback."
