# Tooling

Installed for this VM only on 2026-11-20. No third-party skill files are committed.

| Tool | Source | Version | Why | Check |
| --- | --- | --- | --- | --- |
| superpowers skills | already present in the session | n/a | plans, TDD, debugging, verification | used as guidance |
| ponytail | `npx skills add DietrichGebert/ponytail` | latest on 2026-11-20 | keep code small | installed, loaded at session start |
| caveman | `npx skills add JuliusBrussee/caveman --skill caveman` | latest on 2026-11-20 | short progress notes | installed, not used for files |
| humanizer | `npx skills add blader/humanizer` | latest on 2026-11-20 | docs pass before release | installed |
| gitleaks | `go install github.com/zricethezav/gitleaks/v8@latest` | v8.30.1 | secret scan before every commit | ok |
| actionlint | `go install github.com/rhysd/actionlint/cmd/actionlint@latest` | latest on 2026-11-20 | check workflow files | ok |
| pip-audit | `uv tool install pip-audit` | latest on 2026-11-20 | dependency check | ok |
| pre-commit | `uv tool install pre-commit` | latest on 2026-11-20 | runs gitleaks as a hook | ok |
| cisco-ai-skill-scanner | `uv tool install cisco-ai-skill-scanner` | latest on 2026-11-20 | scan new skills | installed, no new skill needed |
| ruff | in the VM and in `.[dev]` | 0.5+ | lint and `--select S` security rules | ok |

Skipped: graphify (the codebase stays under 30 source files), semgrep and osv-scanner (their hosts are blocked by the proxy), rtk (optional), security-audit (the brief says skip it).
