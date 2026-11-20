import hashlib
import json
import re
from pathlib import Path

from conftest import FIXTURES, FakeClock, serve_repos

from census import analyze, dataset, report, sample
from census.collect import collect
from census.http import Fetcher
from census.stats import wilson

ROOT = Path(__file__).resolve().parents[1]


def fetcher(tmp_path):
    c = FakeClock()
    return Fetcher(tmp_path / "cache", sleep=c.sleep, clock=c.time, today=lambda: "2026-11-20")


def test_wilson_known_values():
    lo, hi = wilson(5, 10)
    assert (round(lo, 4), round(hi, 4)) == (0.2366, 0.7634)
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and round(hi, 4) == 0.2775
    assert wilson(0, 0) == (0.0, 0.0)


def test_strata_and_query():
    assert len(list(sample.strata())) == 72
    q = sample.stratum_query("Go", ">=1000", 2025)
    assert q == "language:Go stars:>=1000 pushed:2025-01-01..2025-12-31 fork:false archived:false"


def test_sampler_saves_queries_and_is_seeded(server, tmp_path):
    page = json.loads((FIXTURES / "search_page.json").read_text())
    server.routes["/search/repositories"] = [(200, {}, page)]
    rows1, meta1 = sample.sample(fetcher(tmp_path / "a"), 3, seed=7, api=server.url)
    rows2, meta2 = sample.sample(fetcher(tmp_path / "b"), 3, seed=7, api=server.url)
    assert rows1 == rows2 and meta1 == meta2
    assert len(meta1["queries"]) == 72 and meta1["sampled_on"] == "2026-11-20"
    assert {r["repo"] for r in rows1} == {
        "fixture-org/alpha",
        "fixture-org/beta",
        "fixture-org/gamma",
    }
    sample.write_sample(rows1, meta1, tmp_path / "data")
    assert sample.read_sample(tmp_path / "data")[0]["repo"] == "fixture-org/alpha"


def test_file_stats_sections_and_pointer():
    text = "# Guide\n\n## Commands\n\nx\n\n## Testing\n\ny\n\n## Boundaries\n\nNever push.\n"
    s = analyze.file_stats(text)
    assert s["headings"] == 4 and s["sec_commands"] and s["sec_testing"] and s["sec_boundaries"]
    assert not s["sec_style"]
    assert analyze.is_pointer("See AGENTS.md\n")
    assert analyze.is_pointer("AGENTS.md")  # what raw serves for a symlink
    assert not analyze.is_pointer(text)


def test_overlap():
    a = "line one here\nline two here\nline three\n"
    assert analyze.jaccard(a, a) == 1.0
    assert analyze.max_overlap([a, "See AGENTS.md"]) is None
    assert 0 < analyze.max_overlap([a, "line one here\nsomething else\n"]) < 1


def _run_pipeline(server, tmp_path, fixture_repos):
    serve_repos(server, fixture_repos)
    data = tmp_path / "data"
    rows = [
        {
            "repo": r,
            "language": "Python",
            "star_band": "100..999",
            "push_year": 2025,
            "default_branch": "main",
            "stratum": "Python|100..999|2025",
        }
        for r in sorted(fixture_repos)
    ]
    sample.write_sample(rows, {"seed": 1, "queries": []}, data)
    cache = tmp_path / "cache"
    collect(
        fetcher(tmp_path), [r["repo"] for r in rows], cache / "collect_state.jsonl", raw=server.url
    )
    return cache, data


def _digest(folder: Path) -> dict:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.iterdir())
        if p.is_file()
    }


def test_rebuild_from_cache_is_byte_for_byte(server, tmp_path, fixture_repos):
    """Broken case: unsorted rows, set order or a build timestamp change the bytes."""
    cache, data = _run_pipeline(server, tmp_path, fixture_repos)
    res = tmp_path / "results"
    dataset.build(cache, data, res, raw=server.url)
    first = _digest(data) | {"summary": _digest(res)["summary.json"]}
    hits = len(server.hits)
    dataset.build(cache, data, res, raw=server.url)
    assert len(server.hits) == hits  # the rebuild reads only the cache
    second = _digest(data) | {"summary": _digest(res)["summary.json"]}
    assert first == second


def test_dataset_counts_and_privacy(server, tmp_path, fixture_repos):
    cache, data = _run_pipeline(server, tmp_path, fixture_repos)
    s = dataset.build(cache, data, tmp_path / "results", raw=server.url)
    assert s["n_repos"] == 4 and s["n_files"] == 6
    head = {p["label"]: p for p in s["headline"]}
    assert head["Repos with at least one agent instruction file"]["k"] == 3
    assert head["Files that only point to another instruction file"]["k"] == 1
    drift = head["Checkable commands that drift"]
    assert (drift["k"], drift["n"]) == (2, 6)  # drift: alpha npm lint, beta make docs
    released = "".join(p.read_text() for p in data.glob("census_*"))
    for files in fixture_repos.values():
        for body in files.values():
            for line in body.splitlines():
                if len(line) > 12:
                    assert line not in released, "file text leaked into the dataset"
    assert not re.search(r"[\w.]+@[\w-]+\.\w+", released)


def test_report_site_and_readme_table(server, tmp_path, fixture_repos):
    cache, data = _run_pipeline(server, tmp_path, fixture_repos)
    res = tmp_path / "results"
    dataset.build(cache, data, res, raw=server.url)
    report.build_site(res, tmp_path / "site")
    page = (tmp_path / "site/index.html").read_text()
    assert "Wilson" in page and "fixture-org" not in page
    readme = tmp_path / "README.md"
    readme.write_text(f"top\n{report.START}\nold\n{report.END}\nbottom\n")
    report.update_readme(readme, res)
    assert "75.0% (30.1 to 95.4)" in readme.read_text()  # 3 of 4 repos


def test_shipped_readme_matches_results():
    """A README number that does not match its results file fails here."""
    summary, ev = report.load(ROOT / "results")
    text = (ROOT / "README.md").read_text()
    block = text.split(report.START, 1)[1].split(report.END, 1)[0].strip()
    assert block == report.readme_table(summary, ev)
