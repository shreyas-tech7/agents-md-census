"""Stratified sampler over the GitHub Search API.

Strata are language x star band x last-push year. Inside each stratum the
sampler picks one seeded random results page, so the sample is not just the
first page of search results.
"""

from __future__ import annotations

import csv
import json
import random
import urllib.parse
from pathlib import Path

from census.http import Fetcher

API = "https://api.github.com"
LANGUAGES = ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "Ruby"]
STAR_BANDS = ["10..99", "100..999", ">=1000"]
PUSH_YEARS = [2024, 2025, 2026]
SEARCH_CAP = 1000  # the Search API never returns more than 1,000 results per query
SAMPLE_FIELDS = ["repo", "language", "star_band", "push_year", "default_branch", "stratum"]


def strata():
    for lang in LANGUAGES:
        for band in STAR_BANDS:
            for year in PUSH_YEARS:
                yield lang, band, year


def stratum_query(lang: str, band: str, year: int) -> str:
    return (
        f"language:{lang} stars:{band} pushed:{year}-01-01..{year}-12-31 fork:false archived:false"
    )


def search_url(query: str, per_page: int, page: int, api: str = API) -> str:
    q = urllib.parse.quote(query, safe=":.=<>")
    return f"{api}/search/repositories?q={q}&per_page={per_page}&page={page}"


def sample(fetcher: Fetcher, per_stratum: int, seed: int, api: str = API) -> tuple[list, dict]:
    """Return (rows, query_log). Two search calls per stratum: one count, one page."""
    rng = random.Random(seed)  # noqa: S311 (sampling, not security)
    rows, log = [], []
    seen = set()
    for lang, band, year in strata():
        query = stratum_query(lang, band, year)
        count_resp = fetcher.get(search_url(query, 1, 1, api))
        if count_resp.status != 200:
            log.append({"query": query, "status": count_resp.status, "total_count": None})
            continue
        total = count_resp.json()["total_count"]
        per_page = per_stratum
        pages = max(1, min(total, SEARCH_CAP) // per_page)
        page = rng.randint(1, pages)
        resp = fetcher.get(search_url(query, per_page, page, api))
        log.append(
            {
                "query": query,
                "status": resp.status,
                "total_count": total,
                "page": page,
                "per_page": per_page,
                "fetched_on": resp.fetched_on,
            }
        )
        if resp.status != 200:
            continue
        for item in resp.json().get("items", []):
            name = item["full_name"]
            if name in seen:
                continue
            seen.add(name)
            rows.append(
                {
                    "repo": name,
                    "language": lang,
                    "star_band": band,
                    "push_year": year,
                    "default_branch": item.get("default_branch", "HEAD"),
                    "stratum": f"{lang}|{band}|{year}",
                }
            )
    dates = sorted({e["fetched_on"] for e in log if e.get("fetched_on")})
    meta = {
        "seed": seed,
        "per_stratum": per_stratum,
        "sampled_on": dates[-1] if dates else None,
        "queries": log,
    }
    rows.sort(key=lambda r: r["repo"].lower())
    return rows, meta


def write_sample(rows: list, meta: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SAMPLE_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    (out_dir / "queries.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")


def read_sample(out_dir: Path) -> list[dict]:
    with open(out_dir / "sample.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
