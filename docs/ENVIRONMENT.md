# Environment probes

Probed on 2026-11-20 from the Claude Code cloud session, with `curl -sS -o /dev/null -w '%{http_code}' -m 10 <url>`.

| URL | Answer | Meaning |
| --- | --- | --- |
| `https://api.github.com/search/repositories?q=stars:%3E50&per_page=1` | 200 | Search works. Headers show `X-RateLimit-Limit: 30` and `X-RateLimit-Resource: search`, the authenticated search limit. |
| `https://api.github.com/repos/octocat/Hello-World/git/trees/HEAD` | 403 | Trees of other repos are blocked by the session proxy. |
| `https://raw.githubusercontent.com/octocat/Hello-World/HEAD/README` | 200 | Raw files work. A missing file answers 404. |
| `https://pypi.org/pypi/agents-md-census/json` | 404 | Name is free on PyPI. |
| `https://registry.npmjs.org/agents-md-census` | 404 | Name is free on npm. |
| `https://huggingface.co` | blocked (proxy 403) | Not needed. |
| `https://api.osv.dev` | blocked (proxy 403) | pip-audit falls back to the PyPI advisory source. |
| `https://semgrep.dev` | blocked (proxy 403) | Use `ruff check --select S` instead. |

Tokens: `GH_TOKEN` and `GITHUB_TOKEN` both hold the placeholder `proxy-injected`. The code treats that as no token. The proxy adds its own token to Search calls outside the VM.

Proxy quirk: on Search answers, `X-RateLimit-Remaining` stays at 30 while `X-RateLimit-Used` climbs. The fetcher treats `used >= limit` as a spent budget and waits for `X-RateLimit-Reset` (test `test_used_against_limit_counts_as_exhausted`).

## Path taken

Path 2 from the brief: search works and trees answer 403. The sampler uses Search. The collector reads fixed paths from `raw.githubusercontent.com`. `.cursor/rules/` folders and nested `SKILL.md` files are not covered in the pilot.

Machine: Python 3.13 in the VM (CI uses 3.11), uv 0.11, Go for gitleaks and actionlint.
