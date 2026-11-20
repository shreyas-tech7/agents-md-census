"""Build the released dataset and the summary from the cache alone.

The output holds repo names and computed numbers only. It holds no file
text, no author names and no emails. Every output is sorted with a fixed
field order and holds no timestamp except the collection date, so a rerun
from the same cache gives the same bytes.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

from census import analyze, drift
from census.collect import INSTRUCTION_FILES, MANIFESTS, RAW, StateLog, raw_url
from census.http import Fetcher
from census.sample import read_sample
from census.stats import proportion

FILE_KEY = {
    "AGENTS.md": "agents_md",
    "CLAUDE.md": "claude_md",
    ".github/copilot-instructions.md": "copilot",
    "GEMINI.md": "gemini_md",
    "SKILL.md": "skill_md",
    ".cursorrules": "cursorrules",
}
REPO_FIELDS = (
    ["repo", "language", "star_band", "push_year"]
    + [f"has_{v}" for v in FILE_KEY.values()]
    + ["n_instruction_files", "has_package_json", "has_makefile", "has_pyproject", "max_overlap"]
)
FILE_FIELDS = [
    "repo", "file", "bytes", "lines", "words", "headings", "is_pointer",
    "sec_commands", "sec_style", "sec_testing", "sec_architecture", "sec_boundaries",
    "n_commands", "n_ok", "n_drift", "n_unverifiable",
]  # fmt: skip


def _write(rows: list[dict], fields: list[str], stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    with open(stem.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(r[k]) for k in fields})
    with open(stem.with_suffix(".jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in fields}, separators=(",", ":")) + "\n")


def _cell(v):
    if isinstance(v, bool):
        return int(v)
    return "" if v is None else v


def analyze_repo(fetcher: Fetcher, repo: str, raw: str) -> tuple[dict, list[dict], list[str]]:
    bodies, dates = {}, []
    for path in INSTRUCTION_FILES + MANIFESTS:
        r = fetcher.cached(raw_url(repo, path, raw))
        if r is None:
            if path in MANIFESTS and not bodies:
                continue  # no instruction file, so the manifests were never fetched
            raise KeyError(f"not cached: {repo} {path}")
        dates.append(r.fetched_on)
        if r.status == 200:
            bodies[path] = r.body
    manifests = drift.parse_manifests({k: v for k, v in bodies.items() if k in MANIFESTS})
    files = []
    for path in INSTRUCTION_FILES:
        if path not in bodies:
            continue
        stats = analyze.file_stats(bodies[path])
        rep = drift.drift_report(bodies[path], manifests)
        files.append(
            {
                "repo": repo,
                "file": path,
                **stats,
                **{k: rep[k] for k in ("n_commands", "n_ok", "n_drift", "n_unverifiable")},
            }
        )
    texts = [bodies[p] for p in INSTRUCTION_FILES if p in bodies]
    row = {
        **{f"has_{v}": k in bodies for k, v in FILE_KEY.items()},
        "n_instruction_files": len(texts),
        # Manifests are only fetched for repos with an instruction file. Blank otherwise.
        "has_package_json": ("package.json" in bodies) if texts else None,
        "has_makefile": ("Makefile" in bodies) if texts else None,
        "has_pyproject": ("pyproject.toml" in bodies) if texts else None,
        "max_overlap": analyze.max_overlap(texts),
    }
    return row, files, dates


def build(cache: Path, data: Path, results: Path, raw: str = RAW) -> dict:
    fetcher = Fetcher(cache)
    sample = read_sample(data)
    state = StateLog(cache / "collect_state.jsonl").state
    repos, files, dates = [], [], []
    for s in sample:
        if state.get(s["repo"]) != "done":
            continue
        row, frows, d = analyze_repo(fetcher, s["repo"], raw)
        repos.append(
            {
                "repo": s["repo"],
                "language": s["language"],
                "star_band": s["star_band"],
                "push_year": int(s["push_year"]),
                **row,
            }
        )
        files.extend(frows)
        dates.extend(d)
    repos.sort(key=lambda r: r["repo"].lower())
    files.sort(key=lambda r: (r["repo"].lower(), r["file"]))
    _write(repos, REPO_FIELDS, data / "census_repos")
    _write(files, FILE_FIELDS, data / "census_files")
    summary = summarize(repos, files, len(sample), sorted(set(dates)))
    results.mkdir(parents=True, exist_ok=True)
    (results / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def summarize(repos: list[dict], files: list[dict], n_sampled: int, dates: list[str]) -> dict:
    date = dates[-1] if dates else None
    n = len(repos)

    def prop(k, n_, label, unit):
        return proportion(k, n_, date=date, label=label, unit=unit)

    with_any = [r for r in repos if r["n_instruction_files"] > 0]
    real = [f for f in files if not f["is_pointer"]]
    checked = [f for f in files if f["n_ok"] + f["n_drift"] > 0]
    n_checked_cmds = sum(f["n_ok"] + f["n_drift"] for f in files)
    headline = [
        prop(len(with_any), n, "Repos with at least one agent instruction file", "repos"),
        *[
            prop(sum(r[f"has_{v}"] for r in repos), n, f"Repos with {k}", "repos")
            for k, v in FILE_KEY.items()
        ],
        prop(
            sum(r["n_instruction_files"] >= 2 for r in with_any),
            len(with_any),
            "Repos with a file that use two or more formats",
            "repos with a file",
        ),
        prop(
            sum(f["is_pointer"] for f in files),
            len(files),
            "Files that only point to another instruction file",
            "files",
        ),
        *[
            prop(
                sum(f[f"sec_{s}"] for f in real),
                len(real),
                f"Files with {'an' if s[0] in 'aeiou' else 'a'} {s} section",
                "non-pointer files",
            )
            for s in ("commands", "testing", "style", "architecture", "boundaries")
        ],
        prop(
            sum(f["n_drift"] > 0 for f in checked),
            len(checked),
            "Files with at least one drifted command",
            "files with a checkable command",
        ),
        prop(
            sum(f["n_drift"] for f in files),
            n_checked_cmds,
            "Checkable commands that drift",
            "checkable commands",
        ),
    ]
    by = {}
    for key in ("language", "star_band", "push_year"):
        groups = sorted({r[key] for r in repos}, key=str)
        by[key] = [
            prop(
                sum(r["n_instruction_files"] > 0 for r in repos if r[key] == g),
                sum(r[key] == g for r in repos),
                f"{key}={g}",
                "repos",
            )
            for g in groups
        ]
    lines = [f["lines"] for f in real]
    return {
        "collection_dates": [dates[0], dates[-1]] if dates else [],
        "n_sampled": n_sampled,
        "n_repos": n,
        "n_files": len(files),
        "n_non_pointer_files": len(real),
        "n_commands_found": sum(f["n_commands"] for f in files),
        "n_commands_checkable": n_checked_cmds,
        "median_lines": statistics.median(lines) if lines else None,
        "headline": headline,
        "any_file_by": by,
    }
