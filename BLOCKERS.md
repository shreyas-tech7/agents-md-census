# Blockers

Each entry: what failed, the exact error, and what was done instead.

1. **Tree calls for other repos are refused.** `GET https://api.github.com/repos/octocat/Hello-World/git/trees/HEAD` answered `403` on 2026-11-20. Instead: collection reads fixed paths from `raw.githubusercontent.com` (brief path 2). `.cursor/rules/` and nested `SKILL.md` are not covered.
2. **No real token in the VM.** `GH_TOKEN` and `GITHUB_TOKEN` hold `proxy-injected`. Instead: the code sends no token. The proxy authenticates Search outside the VM, which gave the 30-a-minute search limit.
3. **Search slowed by the proxy budget.** The proxy keeps `X-RateLimit-Remaining` at 30 while `X-RateLimit-Used` climbs, so the first sampler run backed off 60 seconds at a time. Instead: the fetcher now treats `used >= limit` as spent and waits for the reset. Test: `test_used_against_limit_counts_as_exhausted`.
4. **Raw fetches slowed to one request a second.** After a secondary limit the fetcher drops to one request a second, as the brief's fallback says. Instead: manifests are fetched only for repos that have an instruction file, which cuts requests by a third, and collection runs in chunks of 200 to 400 repos.
5. **GitHub Actions, repo settings, PRs, tags and releases cannot be reached.** There is no GitHub repo for this project in this session. The origin is a local bare repo. Instead: CI steps run locally through `./init.sh`, and the GitHub steps are in `docs/HUMAN_STEPS.md`.
6. **semgrep.dev and api.osv.dev are blocked** (`CONNECT tunnel failed, response 403`). Instead: `ruff check --select S` and `pip-audit` against PyPI.

Bug log (frequency x severity):

- Live bug, fixed: the sampler used an undefined `per_page` on the first run (5 x 5 = 25). Fixed before any data was written.
- Test gap, logged: the detector misses PowerShell prompt lines and commands inside `bash -c "..."` (held-out H01 and H03). Score 2 x 2 = 4. Logged in `LIMITATIONS.md`, not fixed, to keep the held-out set honest.
