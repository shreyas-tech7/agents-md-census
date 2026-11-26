"""Static report site and the generated README tables.

Nobody types a number. Both outputs come from results/summary.json and
results/drift_eval.json. The report shows totals only, never one repo.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

START, END = "<!-- results:start -->", "<!-- results:end -->"


def load(results: Path) -> tuple[dict, dict | None]:
    summary = json.loads((results / "summary.json").read_text())
    ev = results / "drift_eval.json"
    return summary, json.loads(ev.read_text()) if ev.exists() else None


def _fmt(p: dict) -> str:
    if p["pct"] is None:
        return "n/a"
    return f"{p['pct']}% ({p['ci_low']} to {p['ci_high']})"


def readme_table(summary: dict, ev: dict | None) -> str:
    dates = summary["collection_dates"]
    lines = [
        (
            f"Sample: {summary['n_repos']} public repos collected on "
            f"{' to '.join(dict.fromkeys(dates))}, out of {summary['n_sampled']} sampled. "
            "Intervals are 95% Wilson score intervals. Counts have no model and no seed. "
            "The sample seed is in `data/queries.json`."
        ),
        "",
        "| Measure | Result (95% CI) | k / n | Unit |",
        "| --- | --- | --- | --- |",
    ]
    for p in summary["headline"]:
        lines.append(f"| {p['label']} | {_fmt(p)} | {p['k']} / {p['n']} | {p['unit']} |")
    for name, p in _eval_rows(ev):
        lines.append(f"| {name} | {_fmt(p)} | {p['k']} / {p['n']} | {p['unit']} |")
    cost = summary.get("cost")
    if cost:
        lines += [
            "",
            (
                f"Cost of this run: {cost['search_requests']} Search API requests, "
                f"{cost['raw_requests']} raw file requests ({cost['raw_requests_per_repo']} per repo), "
                f"{cost['model_calls']} model calls, ${cost['dollars']}. These are fixed counts."
            ),
        ]
    return "\n".join(lines)


def _eval_rows(ev: dict | None) -> list[tuple[str, dict]]:
    if not ev:
        return []
    rows = [
        (f"Drift detector precision, {ev['n_snippets']} labeled snippets", ev["precision"]),
        (f"Drift detector recall, {ev['n_snippets']} labeled snippets", ev["recall"]),
    ]
    if "heldout" in ev:
        h = ev["heldout"]
        rows += [
            (f"Drift detector precision, {h['n_snippets']} held-out snippets", h["precision"]),
            (f"Drift detector recall, {h['n_snippets']} held-out snippets", h["recall"]),
        ]
    if "label_agreement" in ev:
        rows.append(("Two independent agent labelers agree on a snippet", ev["label_agreement"]))
    return rows


def update_readme(readme: Path, results: Path) -> bool:
    summary, ev = load(results)
    text = readme.read_text(encoding="utf-8")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    new = f"{head}{START}\n{readme_table(summary, ev)}\n{END}{tail}"
    changed = new != text
    readme.write_text(new, encoding="utf-8")
    return changed


def _rows(props: list[dict]) -> str:
    out = []
    for p in props:
        width = p["pct"] or 0
        out.append(
            "<tr><td>{}</td><td class=num>{}</td><td class=num>{} / {}</td>"
            "<td><div class=bar><span style='width:{}%'></span></div></td></tr>".format(
                html.escape(p["label"]), html.escape(_fmt(p)), p["k"], p["n"], width
            )
        )
    return "\n".join(out)


def build_site(results: Path, site: Path) -> None:
    summary, ev = load(results)
    dates = " to ".join(dict.fromkeys(summary["collection_dates"]))
    sections = [
        (
            f"<h2>Headline numbers</h2><table><tr><th>Measure</th><th>Result (95% CI)</th>"
            f"<th>k / n</th><th></th></tr>{_rows(summary['headline'])}</table>"
        )
    ]
    for key, title in (
        ("language", "Language"),
        ("star_band", "Star band"),
        ("push_year", "Last push year"),
    ):
        sections.append(
            f"<h2>Repos with any instruction file, by {title.lower()}</h2>"
            f"<table><tr><th>{title}</th><th>Result (95% CI)</th><th>k / n</th><th></th></tr>"
            f"{_rows(summary['any_file_by'][key])}</table>"
        )
    if ev:
        sections.append(
            "<h2>Drift detector check</h2><table><tr><th>Measure</th><th>Result (95% CI)</th>"
            f"<th>k / n</th><th></th></tr>"
            f"{_rows([{**p, 'label': name} for name, p in _eval_rows(ev)])}</table>"
            f"<p>Scored on synthetic snippets labeled on {ev['date']}. The held-out set was "
            "written by a separate agent and the detector was not tuned on it.</p>"
        )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agents-md-census report</title>
<style>
:root {{ --fg:#1b1f24; --muted:#57606a; --bg:#ffffff; --bar:#2f6feb; --line:#d0d7de; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg:#e6edf3; --muted:#9198a1; --bg:#0d1117; --bar:#4493f8; --line:#30363d; }} }}
body {{ font: 16px/1.5 system-ui, sans-serif; color: var(--fg); background: var(--bg); max-width: 980px; margin: 0 auto; padding: 16px; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0 24px; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: middle; }}
td.num {{ white-space: nowrap; font-variant-numeric: tabular-nums; }}
.bar {{ background: var(--line); height: 10px; width: 160px; border-radius: 5px; overflow: hidden; }}
.bar span {{ display: block; height: 100%; background: var(--bar); }}
p.meta {{ color: var(--muted); }}
@media (max-width: 640px) {{ .bar {{ width: 60px; }} th, td {{ padding: 4px; font-size: 14px; }} }}
</style></head><body>
<h1>agents-md-census report</h1>
<p class=meta>{summary["n_repos"]} public repos collected on {html.escape(dates)}, out of
{summary["n_sampled"]} sampled across language, star band and last push year.
{summary["n_files"]} instruction files found. Every percentage has a 95% Wilson score interval.
This page shows totals only and never names a single repo.
See METHODOLOGY.md and LIMITATIONS.md in the repo for how the numbers were made.</p>
{"".join(sections)}
</body></html>
"""
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text(page, encoding="utf-8")
